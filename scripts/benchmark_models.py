"""Compare candidate Groq models on the same live FX chat evaluation cases."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.prompts import CHAT_PROMPT_VERSION, CHAT_SYSTEM_PROMPT
from scripts.run_chat_eval import CASES, score_answer

BASE_URL = os.getenv("FIELDNOTE_API_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.getenv("GROQ_API_KEY", "").strip()
MODELS = [value.strip() for value in os.getenv("FIELDNOTE_BENCHMARK_MODELS", os.getenv("GROQ_MODEL", "")).split(",") if value.strip()]


async def benchmark_one(provider: httpx.AsyncClient, model: str, case: dict, snapshot: dict) -> dict:
    context = {key: snapshot.get(key) for key in ("ticker", "pair", "timeframe", "price", "change_pips", "pip_size", "indicators", "as_of", "source")}
    system = CHAT_SYSTEM_PROMPT + "\n\nContexte vérifié disponible:\n" + json.dumps(context, ensure_ascii=False)
    started = time.perf_counter()
    try:
        response = await provider.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={"model": model, "temperature": 0, "max_completion_tokens": 1200,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": case["prompt"]}]},
            timeout=45,
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        if response.is_error:
            return {"model": model, "case_id": case["id"], "passed": False,
                    "latency_ms": latency_ms, "failures": [f"provider_http_{response.status_code}"]}
        answer = response.json()["choices"][0]["message"]["content"]
        failures = score_answer(answer if isinstance(answer, str) else "", case)
        return {"model": model, "case_id": case["id"], "passed": not failures,
                "latency_ms": latency_ms, "failures": failures}
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        return {"model": model, "case_id": case["id"], "passed": False,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "failures": [type(error).__name__]}


async def main() -> int:
    if not API_KEY or not MODELS:
        print("Configure GROQ_API_KEY et FIELDNOTE_BENCHMARK_MODELS (liste séparée par des virgules).", file=sys.stderr)
        return 2

    results = []
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=40) as app_client, \
            httpx.AsyncClient() as provider:
        snapshots = {}
        for case in CASES["cases"]:
            key = (case["ticker"], case["timeframe"])
            if key not in snapshots:
                response = await app_client.get(f"/api/market/{case['ticker']}", params={"timeframe": case["timeframe"]})
                response.raise_for_status()
                snapshots[key] = response.json()
            for model in MODELS:
                results.append(await benchmark_one(provider, model, case, snapshots[key]))

    summary = {
        "suite": "forex-model-comparison", "prompt_version": CHAT_PROMPT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(), "models": MODELS,
        "criteria": "Required concepts, unsafe-claim exclusions, and latency; not a financial forecast evaluation.",
        "results": results,
        "by_model": {model: {"passed": sum(row["passed"] for row in results if row["model"] == model),
                             "total": sum(row["model"] == model for row in results),
                             "mean_latency_ms": round(sum(row["latency_ms"] for row in results if row["model"] == model) /
                                                      max(1, sum(row["model"] == model for row in results)), 1)}
                     for model in MODELS},
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "evals" / "results" / f"model_benchmark_{stamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nRapport enregistré dans {output}")
    return 0 if all(row["passed"] for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
