from __future__ import annotations

from agents.risk import assess as assess_risk
from agents.technical import assess as assess_technical


def run(snapshot: dict, news: dict | None = None, macro: dict | None = None,
        sentiment: dict | None = None) -> dict:
    """Run independent specialists before the language-model synthesis step."""
    return {
        "architecture": "hybrid-specialists-v1",
        "technical": assess_technical(snapshot),
        "risk": assess_risk(snapshot),
        "news": news or {"status": "unavailable", "headlines": [], "reason": "Flux indisponible."},
        "sentiment": sentiment or {"agent": "news_sentiment", "status": "unavailable",
                                   "sentiment": "unclear", "summary": "Aucune classification réalisée.", "evidence": []},
        "macro": macro or {"status": "unavailable", "observations": [], "reason": "Séries indisponibles."},
        "supervisor": {"agent": "lead_analyst", "status": "model_synthesis_pending"},
    }
