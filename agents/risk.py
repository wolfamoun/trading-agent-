from __future__ import annotations


def assess(snapshot: dict) -> dict:
    """Flag observable market-risk conditions without inventing a client profile."""
    indicators = snapshot["indicators"]
    price = float(snapshot["price"])
    atr = indicators.get("atr14")
    adx = indicators.get("adx14")
    change_pips = float(snapshot.get("change_pips") or 0)
    atr_pct = (float(atr) / price * 100) if atr is not None and price > 0 else None
    flags: list[str] = []
    if atr_pct is None:
        flags.append("ATR indisponible : impossible de qualifier l’amplitude récente.")
    elif atr_pct >= 0.5:
        flags.append("Amplitude récente élevée par rapport au prix; vérifier le risque de gap et de glissement.")
    elif atr_pct >= 0.2:
        flags.append("Amplitude récente à surveiller avant toute exposition.")
    if adx is not None and adx >= 25:
        flags.append("Tendance marquée : le risque directionnel peut rester élevé; ADX ne prédit pas le sens.")
    if abs(change_pips) >= 2 * float(indicators.get("atr_pips") or 0) > 0:
        flags.append("La dernière bougie dépasse deux ATR; contrôler les nouvelles et la qualité du cours.")
    flags.append("Pas de spread, de liquidité agrégée, de financement overnight ni de profil de compte vérifiés.")
    return {
        "agent": "risk_manager",
        "status": "complete",
        "atr_percent_of_price": round(atr_pct, 4) if atr_pct is not None else None,
        "atr_pips": indicators.get("atr_pips"),
        "market_flags": flags,
        "position_size": None,
        "position_size_note": "Non calculée sans capital, devise du compte, stop et valeur de pip chez le courtier.",
        "limitations": ["Contrôle de marché éducatif; ne constitue ni une allocation personnelle ni un ordre."],
    }
