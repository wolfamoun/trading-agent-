import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

import main


SNAPSHOT = {
    "ticker": "EURUSD=X",
    "pair": "EUR / USD",
    "timeframe": "H1",
    "price": 1.0842,
    "change_pips": 2.4,
    "as_of": "2026-11-10 12:00 UTC",
    "source": "Yahoo Finance · cotations indicatives spot FX",
    "indicators": {"rsi14": 52.4, "atr_pips": 18.2},
}


class ChatApiTests(unittest.TestCase):
    def setUp(self):
        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()
        self.market_patch = patch("main.market_snapshot", new_callable=AsyncMock, return_value=SNAPSHOT)
        self.groq_patch = patch("main.groq_completion", new_callable=AsyncMock, return_value="Un pip EUR/USD correspond à 0,0001.")
        self.market_snapshot = self.market_patch.start()
        self.groq_completion = self.groq_patch.start()

    def tearDown(self):
        self.groq_patch.stop()
        self.market_patch.stop()
        self.client_context.__exit__(None, None, None)

    def test_chat_returns_traceable_response_and_uses_fx_context(self):
        response = self.client.post(
            "/api/chat",
            headers={"X-Request-ID": "chat-eval-001"},
            json={"ticker": "EURUSD=X", "timeframe": "H1", "messages": [
                {"role": "user", "content": "Un pip EUR/USD, ça représente quoi ?"},
            ]},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["answer"], "Un pip EUR/USD correspond à 0,0001.")
        self.assertEqual(body["request_id"], "chat-eval-001")
        self.assertEqual(response.headers["X-Request-ID"], "chat-eval-001")
        self.assertEqual(body["prompt_version"], main.PROMPT_VERSION)
        self.assertTrue(any(source["title"].startswith("OANDA") for source in body["sources"]))
        self.market_snapshot.assert_awaited_once()

        messages = self.groq_completion.await_args.args[0]
        system = messages[0]["content"]
        self.assertIn("Contexte vérifié", system)
        self.assertIn("2026-11-10 12:00 UTC", system)
        self.assertIn("aucun conseil financier personnalisé", system)
        self.assertIn("ne peux pas lire ce graphique", system)
        self.assertIn("BM25 lexical retrieval", system)
        self.assertIn("OANDA · Glossaire forex", system)

    def test_chat_limits_provider_context_to_twelve_recent_turns(self):
        history = [
            {"role": "user" if index % 2 == 0 else "assistant", "content": f"tour-{index}"}
            for index in range(16)
        ]
        response = self.client.post("/api/chat", json={
            "ticker": "EURUSD=X", "timeframe": "H1", "messages": history,
        })

        self.assertEqual(response.status_code, 200)
        provider_messages = self.groq_completion.await_args.args[0]
        self.assertEqual(len(provider_messages), 13)  # system + 12 recent turns
        self.assertEqual(provider_messages[1]["content"], "tour-4")
        self.assertEqual(provider_messages[-1]["content"], "tour-15")

    def test_chat_returns_safe_provider_failure_with_request_id(self):
        self.groq_completion.side_effect = HTTPException(503, "Le service IA est temporairement limité.")
        response = self.client.post(
            "/api/chat", headers={"X-Request-ID": "chat-eval-503"},
            json={"ticker": "EURUSD=X", "timeframe": "H1", "messages": [
                {"role": "user", "content": "Explique le RSI."},
            ]},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("temporairement limité", response.json()["detail"])
        self.assertEqual(response.json()["request_id"], "chat-eval-503")
        self.assertNotIn("Bearer", response.text)

    def test_chat_rejects_invalid_pair_before_calling_model(self):
        self.market_snapshot.side_effect = HTTPException(422, "Choisis une paire suivie.")
        response = self.client.post("/api/chat", json={
            "ticker": "UNKNOWN=X", "timeframe": "H1", "messages": [
                {"role": "user", "content": "Quel est le pip ?"},
            ],
        })

        self.assertEqual(response.status_code, 422)
        self.groq_completion.assert_not_awaited()

    def test_chat_rejects_too_many_turns(self):
        response = self.client.post("/api/chat", json={
            "ticker": "EURUSD=X", "timeframe": "H1", "messages": [
                {"role": "user", "content": f"question-{index}"} for index in range(17)
            ],
        })
        self.assertEqual(response.status_code, 422)
        self.groq_completion.assert_not_awaited()

    def test_chat_rejects_empty_model_answer(self):
        self.groq_completion.return_value = "OK"
        response = self.client.post("/api/chat", json={
            "ticker": "EURUSD=X", "timeframe": "H1", "messages": [
                {"role": "user", "content": "Explique le pip."},
            ],
        })
        self.assertEqual(response.status_code, 502)
        self.assertIn("trop courte", response.json()["detail"])


class AiRateLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_rate_limit_returns_retry_after_without_logging_prompt_content(self):
        host = "rate-limit-regression-test"
        main._ai_rate_windows.pop(host, None)
        request = SimpleNamespace(client=SimpleNamespace(host=host))
        try:
            for _ in range(main._AI_REQUESTS_PER_MINUTE):
                await main.enforce_ai_rate_limit(request)
            with self.assertRaises(HTTPException) as error:
                await main.enforce_ai_rate_limit(request)
            self.assertEqual(error.exception.status_code, 429)
            self.assertIn("Retry-After", error.exception.headers)
        finally:
            main._ai_rate_windows.pop(host, None)


if __name__ == "__main__":
    unittest.main()
