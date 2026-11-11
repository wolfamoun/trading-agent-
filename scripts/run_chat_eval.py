import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "evals" / "forex_chat_cases.json").read_text(encoding="utf-8"))
BASE_URL = os.getenv("FIELDNOTE_API_URL", "http://127.0.0.1:8000").rstrip("/")


async def evaluate_case(client: httpx.AsyncClient, case: dict) -> dict:
    started = time.perf_counter()
    response = await client.post("/api/chat", json={
        "ticker": case["ticker"], "timeframe": case["timeframe"],
        "messages": [{"role": "user", "content": case["prompt"]}],
    })
    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    if response.is_error:
        return {"id": case["id"], "passed": False, "latency_ms": latency_ms,
                "failures": [f"HTTP {response.status_code}"]}
    body = response.json()
    answer = body.get("answer", "")
    failures = score_answer(answer, case)
    return {
        "id": case["id"], "passed": not failures, "latency_ms": latency_ms,
        "prompt_version": body.get("prompt_version"), "model": body.get("model"),
        "request_id": body.get("request_id"), "failures": failures,
    }


def score_answer(answer: str, case: dict) -> list[str]:
    answer = answer.casefold()
    failures = []
    if len(answer) < 30:
        failures.append("answer_too_short")
    if not any(term.casefold() in answer for term in case["must_include_any"]):
        failures.append("required_concept_missing")
    if any(term.casefold() in answer for term in case["must_not_include"]):
        failures.append("unsafe_or_unsupported_claim")
    return failures


async def main() -> int:
    results = []
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=100) as client:
        for case in CASES["cases"]:
            try:
                results.append(await evaluate_case(client, case))
            except (httpx.HTTPError, ValueError) as error:
                results.append({"id": case["id"], "passed": False,
                                "failures": [type(error).__name__]})
    summary = {
        "suite": "forex-chat-quality",
        "prompt_version": CASES["prompt_version"],
        "passed": sum(result["passed"] for result in results),
        "total": len(results),
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
