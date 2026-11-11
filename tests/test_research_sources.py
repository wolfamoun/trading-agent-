import json
import unittest
from unittest.mock import AsyncMock

import httpx

from agents.macro_data import fetch_macro
from agents.news_data import fetch_news
from agents.news_sentiment import assess


class ResearchSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_news_feed_normalizes_sources_and_rejects_insecure_links(self):
        payload = {"news": [
            {"title": "EUR rises after rate decision", "publisher": "Example News",
             "link": "https://example.com/story", "providerPublishTime": 1794330000},
            {"title": "unsafe", "publisher": "Bad", "link": "javascript:alert(1)", "providerPublishTime": 1794330000},
        ]}
        async def handler(_request):
            return httpx.Response(200, json=payload)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await fetch_news("EURUSD=X", client)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["headlines"]), 1)
        self.assertEqual(result["headlines"][0]["publisher"], "Example News")

    async def test_macro_feed_parses_values_and_marks_old_series(self):
        csv_body = "observation_date,DFF,ECBDFR\n2026-01-01,4.0,2.0\n2026-11-10,3.8,2.5\n"
        async def handler(_request):
            return httpx.Response(200, text=csv_body)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await fetch_macro("EURUSD=X", client)
        self.assertEqual(result["status"], "complete")
        self.assertEqual([row["currency"] for row in result["observations"]], ["EUR", "USD"])
        self.assertEqual(result["observations"][0]["value_percent"], 2.5)

    async def test_sentiment_agent_only_keeps_known_evidence_ids(self):
        news = {"status": "complete", "source": "Yahoo", "retrieved_at": "2026-11-10T10:00:00Z",
                "headlines": [{"id": "n1", "title": "EUR market story", "publisher": "Desk",
                               "url": "https://example.com", "published_at": "2026-11-10T09:00:00Z"}]}
        completion = AsyncMock(return_value=json.dumps({
            "sentiment": "mixed", "summary": "Les titres sont partagés.",
            "evidence": [{"headline_id": "n1", "interpretation": "Titre vérifié."},
                         {"headline_id": "invented", "interpretation": "Référence inconnue."}],
        }))
        result = await assess(news, completion)
        self.assertEqual(result["status"], "complete")
        self.assertEqual([item["headline_id"] for item in result["evidence"]], ["n1"])
        self.assertEqual(completion.await_count, 1)


if __name__ == "__main__":
    unittest.main()
