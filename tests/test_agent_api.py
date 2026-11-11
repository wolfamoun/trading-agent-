import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import main


SNAPSHOT = {
    "ticker": "EURUSD=X", "pair": "EUR / USD", "timeframe": "D1", "price": 1.1,
    "change_pips": 4, "pip_size": 0.0001, "bars": [
        {"time": i, "open": 1 + i * .00001, "high": 1 + i * .00002,
         "low": 1 + i * .000005, "close": 1 + i * .00001, "volume": 0}
        for i in range(1, 121)
    ],
    "as_of": "2026-11-10 12:00 UTC", "source": "Yahoo indicatif",
    "indicators": {"ema21": 1.09, "ema50": 1.08, "rsi14": 60, "macd_histogram": .0001,
                    "adx14": 28, "atr14": .001, "atr_pips": 10},
}


class AgentApiTests(unittest.TestCase):
    def setUp(self):
        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)

    def test_analyze_returns_cooperating_reports_and_passes_them_to_supervisor(self):
        news = {"status": "complete", "source": "Yahoo", "headlines": [
            {"id": "n1", "title": "FX headline", "publisher": "Desk", "url": "https://example.com",
             "published_at": "2026-11-10T10:00:00Z"}], "retrieved_at": "2026-11-10T10:00:00Z"}
        macro = {"status": "complete", "source": "FRED", "observations": [], "reason": None}
        sentiment = {"agent": "news_sentiment", "status": "complete", "sentiment": "mixed",
                     "summary": "Titres partagés.", "evidence": [{"headline_id": "n1", "interpretation": "Contexte."}]}
        analysis = {"market_view": "Lecture", "bull_case": "Haussier", "bear_case": "Baissier",
                    "risk_check": "Risque", "decision": "Hold", "confidence": 50, "model": "mock-model"}
        with patch("main.market_snapshot", new_callable=AsyncMock, return_value=SNAPSHOT), \
                patch("main.fetch_news", new_callable=AsyncMock, return_value=news), \
                patch("main.fetch_macro", new_callable=AsyncMock, return_value=macro), \
                patch("main.assess_news_sentiment", new_callable=AsyncMock, return_value=sentiment), \
                patch("main.ask_groq", new_callable=AsyncMock, return_value=analysis) as supervisor:
            response = self.client.post("/api/analyze", json={"ticker": "EURUSD=X", "timeframe": "D1"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["agent_team"]["technical"]["bias"], "bullish")
        self.assertEqual(body["agent_team"]["risk"]["agent"], "risk_manager")
        self.assertEqual(body["agent_team"]["sentiment"]["sentiment"], "mixed")
        self.assertEqual(body["agent_team"]["macro"]["status"], "complete")
        self.assertEqual(body["agent_team"]["supervisor"]["status"], "complete")
        self.assertEqual(supervisor.await_args.args[4]["news"]["headlines"][0]["id"], "n1")

    def test_backtest_endpoint_rejects_invalid_fast_slow_order(self):
        response = self.client.post("/api/backtest", json={
            "ticker": "EURUSD=X", "timeframe": "D1", "fast_period": 30, "slow_period": 10,
        })
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
