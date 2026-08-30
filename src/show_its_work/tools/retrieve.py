"""search_evidence + get_entity_timeline — retrieval over the unstructured trail.

TF-IDF cosine by default: fast, deterministic, no model download — a good fit for a
prototype whose evidence corpus is small. Swappable for embeddings (sentence-
transformers / ChromaDB) behind the same signature. Retrieval is tagged in telemetry
as a non-LLM producer.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..metrics import load_evidence


@lru_cache(maxsize=1)
def _index():
    ev = load_evidence().reset_index(drop=True)
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    mat = vec.fit_transform(ev["text"].tolist())
    return ev, vec, mat


def search_evidence(query: str, window=None, entity_ids: list[str] | None = None,
                    k: int = 6) -> list[dict]:
    ev, vec, mat = _index()
    sims = cosine_similarity(vec.transform([query]), mat).ravel()
    df = ev.copy()
    df["score"] = sims
    if window is not None:
        w0, w1 = pd.Timestamp(window[0]), pd.Timestamp(window[1])
        pad0, pad1 = w0 - pd.Timedelta(days=7), w1 + pd.Timedelta(days=7)
        df = df[(df["timestamp"] >= pad0) & (df["timestamp"] <= pad1)]
    if entity_ids:
        df = df[df["entity_ids"].apply(lambda ids: any(e in ids for e in entity_ids))]
    df = df.sort_values("score", ascending=False).head(k)
    return [{"id": r["id"], "source": r["source"], "text": r["text"],
             "timestamp": str(r["timestamp"]), "entity_ids": list(r["entity_ids"]),
             "score": round(float(r["score"]), 3)} for _, r in df.iterrows()]


def get_entity_timeline(entity_id: str, window=None) -> list[dict]:
    ev = load_evidence()
    df = ev[ev["entity_ids"].apply(lambda ids: entity_id in ids)]
    if window is not None:
        w0, w1 = pd.Timestamp(window[0]), pd.Timestamp(window[1])
        df = df[(df["timestamp"] >= w0 - pd.Timedelta(days=7)) & (df["timestamp"] <= w1 + pd.Timedelta(days=7))]
    df = df.sort_values("timestamp")
    return [{"id": r["id"], "source": r["source"], "text": r["text"],
             "timestamp": str(r["timestamp"]), "entity_ids": list(r["entity_ids"])}
            for _, r in df.iterrows()]
