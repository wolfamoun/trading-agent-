from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_DOCUMENTS = json.loads((ROOT / "knowledge" / "forex_reference.json").read_text(encoding="utf-8"))
_STOPWORDS = {"avec", "dans", "pour", "est", "une", "des", "les", "que", "qui", "sur", "par", "mon", "ma", "mes", "de", "du", "la", "le", "et", "en", "au", "aux", "un", "une", "son", "sa", "ses", "and", "the", "what", "how", "does", "can", "from", "this", "that"}


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return [token for token in re.findall(r"[a-z0-9]+", ascii_text) if len(token) > 1 and token not in _STOPWORDS]


def retrieve(query: str, limit: int = 3) -> list[dict]:
    """Small, auditable BM25 retrieval over cited forex learning references."""
    terms = _tokens(query)
    if not terms:
        return []
    corpus = [set(_tokens(f"{doc['title']} {doc['content']}")) for doc in _DOCUMENTS]
    avgdl = sum(len(tokens) for tokens in corpus) / max(1, len(corpus))
    scores = []
    for doc, tokens in zip(_DOCUMENTS, corpus):
        score = 0.0
        for term in set(terms):
            frequency = sum(1 for token in _tokens(f"{doc['title']} {doc['content']}") if token == term)
            if not frequency:
                continue
            containing = sum(1 for row in corpus if term in row)
            idf = math.log(1 + (len(corpus) - containing + 0.5) / (containing + 0.5))
            denominator = frequency + 1.2 * (0.25 + 0.75 * len(tokens) / max(1, avgdl))
            score += idf * frequency * 2.2 / denominator
        if score > 0:
            scores.append((score, doc))
    scores.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [{**doc, "retrieval_score": round(score, 4)} for score, doc in scores[:max(0, min(limit, 5))]]
