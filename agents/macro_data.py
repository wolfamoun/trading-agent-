from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from io import StringIO

import httpx


SERIES = {
    "USD": ("DFF", "Taux effectif des fonds fédéraux · fréquence quotidienne"),
    "EUR": ("ECBDFR", "Facilité de dépôt BCE · fréquence quotidienne"),
    "GBP": ("IRSTCI01GBM156N", "Taux court terme · série mensuelle"),
    "JPY": ("IRSTCI01JPM156N", "Taux court terme · série mensuelle"),
    "AUD": ("IRSTCI01AUM156N", "Taux court terme · série mensuelle"),
    "CAD": ("IRSTCI01CAM156N", "Taux court terme · série mensuelle"),
    "CHF": ("IRSTCI01CHM156N", "Taux court terme · série mensuelle"),
    "NZD": ("IRSTCI01NZM156N", "Taux court terme · série mensuelle"),
}


async def fetch_macro(ticker: str, client: httpx.AsyncClient) -> dict:
    pair = ticker.removesuffix("=X")
    currencies = [pair[:3], pair[3:6]]
    selected = {currency: SERIES[currency] for currency in currencies if currency in SERIES}
    ids = [series_id for series_id, _ in selected.values()]
    if not ids:
        return {"status": "unavailable", "source": "FRED", "observations": [],
                "reason": "Aucune série macro configurée pour cette paire."}
    start = (datetime.now(timezone.utc) - timedelta(days=120)).date().isoformat()
    try:
        response = await client.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv",
            params={"id": ",".join(ids), "cosd": start}, timeout=15,
        )
        response.raise_for_status()
        rows = list(csv.DictReader(StringIO(response.text)))
    except (httpx.HTTPError, csv.Error, ValueError):
        return {"status": "unavailable", "source": "FRED", "observations": [],
                "reason": "Les séries macro FRED sont momentanément indisponibles."}

    observations = []
    today = datetime.now(timezone.utc).date()
    for currency, (series_id, label) in selected.items():
        latest = None
        for row in rows:
            raw_value = row.get(series_id, "")
            try:
                value = float(raw_value)
                if not raw_value or not value == value or value in (float("inf"), float("-inf")):
                    continue
                latest = (row.get("observation_date"), value)
            except (TypeError, ValueError):
                continue
        if latest is None:
            observations.append({"currency": currency, "series_id": series_id, "label": label, "status": "missing"})
            continue
        date_text, value = latest
        try:
            age_days = (today - datetime.strptime(date_text, "%Y-%m-%d").date()).days
        except (TypeError, ValueError):
            age_days = None
        observations.append({"currency": currency, "series_id": series_id, "label": label,
                             "value_percent": round(value, 4), "observed_at": date_text,
                             "age_days": age_days,
                             "status": "stale" if age_days is None or age_days > 45 else "current"})
    return {"status": "complete" if any(row.get("value_percent") is not None for row in observations) else "no_coverage",
            "source": "Federal Reserve Bank of St. Louis · FRED",
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "observations": observations,
            "reason": "Les séries ont des fréquences et des définitions différentes; comparer leurs valeurs avec prudence."}
