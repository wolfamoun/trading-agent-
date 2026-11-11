from __future__ import annotations

from datetime import datetime, timezone

import httpx


async def fetch_news(ticker: str, client: httpx.AsyncClient) -> dict:
    """Fetch and normalize recent headlines; a failure never fabricates sentiment."""
    pair = ticker.removesuffix("=X")
    try:
        response = await client.get(
            "https://query1.finance.yahoo.com/v1/finance/search",
            params={"q": pair, "newsCount": 12, "quotesCount": 0},
            timeout=12,
        )
        response.raise_for_status()
        raw_items = response.json().get("news", [])
    except (httpx.HTTPError, ValueError, TypeError):
        return {"status": "unavailable", "source": "Yahoo Finance Search", "headlines": [],
                "reason": "Le flux d’actualités n’a pas répondu; aucun sentiment ne sera supposé."}

    headlines = []
    now = datetime.now(timezone.utc).timestamp()
    for item in raw_items:
        title = item.get("title")
        url = item.get("link")
        published = item.get("providerPublishTime")
        if not isinstance(title, str) or not title.strip() or not isinstance(url, str) or not url.startswith("https://"):
            continue
        try:
            timestamp = int(published)
            if timestamp <= 0 or timestamp > now + 86400:
                continue
            published_at = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError, OSError):
            published_at = None
        headlines.append({
            "id": f"n{len(headlines) + 1}", "title": title.strip()[:400],
            "publisher": str(item.get("publisher") or "Source non précisée")[:120],
            "url": url, "published_at": published_at,
        })
        if len(headlines) >= 8:
            break
    return {"status": "complete" if headlines else "no_coverage", "source": "Yahoo Finance Search",
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "headlines": headlines,
            "reason": None if headlines else "Aucun titre exploitable n’a été trouvé pour cette requête."}
