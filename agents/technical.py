from __future__ import annotations


def assess(snapshot: dict) -> dict:
    """Turn already-computed FX indicators into explicit, inspectable evidence."""
    indicators = snapshot["indicators"]
    price = float(snapshot["price"])
    evidence: list[dict] = []
    score = 0

    ema21 = indicators.get("ema21")
    ema50 = indicators.get("ema50")
    if ema21 is not None and ema50 is not None:
        if price > ema21 > ema50:
            score += 1
            evidence.append({"signal": "trend", "side": "bullish", "reason": "Cours au-dessus des EMA 21 et 50."})
        elif price < ema21 < ema50:
            score -= 1
            evidence.append({"signal": "trend", "side": "bearish", "reason": "Cours sous les EMA 21 et 50."})
        else:
            evidence.append({"signal": "trend", "side": "mixed", "reason": "Les moyennes mobiles ne sont pas alignées."})

    rsi = indicators.get("rsi14")
    if rsi is not None:
        if rsi >= 55:
            score += 1
            side = "bullish"
        elif rsi <= 45:
            score -= 1
            side = "bearish"
        else:
            side = "mixed"
        evidence.append({"signal": "rsi14", "side": side, "value": rsi,
                         "reason": f"RSI 14 à {rsi:.1f}; seuils de contexte 45/55, pas des déclencheurs."})

    macd = indicators.get("macd_histogram")
    if macd is not None:
        if macd > 0:
            score += 1
            side = "bullish"
        elif macd < 0:
            score -= 1
            side = "bearish"
        else:
            side = "mixed"
        evidence.append({"signal": "macd_histogram", "side": side, "value": macd,
                         "reason": "Histogramme MACD positif." if macd > 0 else "Histogramme MACD négatif." if macd < 0 else "Histogramme MACD neutre."})

    adx = indicators.get("adx14")
    if adx is not None:
        evidence.append({"signal": "adx14", "side": "strength" if adx >= 25 else "weak",
                         "value": adx, "reason": "L’ADX mesure la force de tendance, pas sa direction ni sa rentabilité."})

    bias = "bullish" if score >= 2 else "bearish" if score <= -2 else "mixed"
    return {
        "agent": "technical",
        "status": "complete",
        "bias": bias,
        "score": score,
        "evidence": evidence,
        "limitations": ["Règles descriptives et fixes; aucun seuil n’assure une performance future."],
    }
