"""
Cross-encoder re-ranker.

Re-ranks the top-N candidates from hybrid search with a cross-encoder that
jointly encodes the query and each candidate. Cross-encoders are slower than
bi-encoders but much more accurate — that's why we use them on a small
candidate set (typically top-20 from hybrid → top-5).
"""
from __future__ import annotations

import os

# Silence HF noise
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

from sentence_transformers import CrossEncoder

from app.config import settings


class Reranker:
    """Lazy-loaded singleton wrapper around sentence-transformers CrossEncoder."""

    _instance: Reranker | None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_name: str | None = None):
        if getattr(self, "_initialized", False):
            return
        self.model_name = model_name or settings.reranker_model
        self.model = CrossEncoder(self.model_name)
        self._initialized = True

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int | None = None,
    ) -> list[dict]:
        """Re-rank candidates for a query.

        Each candidate is a dict with at least ``text``. The returned list
        preserves the original dict but adds ``rerank_score`` (raw sigmoid
        score) and updates ``score`` to the normalized rank-fusion+rerank
        score in [0, 1].

        Args:
            query: The query string.
            candidates: List of candidate dicts from hybrid search.
            top_k: Number of results to return. Defaults to settings.top_k_rerank.
        """
        if not candidates:
            return []

        top_k = top_k or settings.top_k_rerank
        top_k = min(top_k, len(candidates))

        pairs = [(query, c.get("text", "")) for c in candidates]
        raw_scores = self.model.predict(pairs, show_progress_bar=False)

        # Attach scores and sort
        for c, s in zip(candidates, raw_scores, strict=False):
            c["rerank_score"] = float(s)

        sorted_candidates = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)[:top_k]

        # Normalize rerank scores in [0, 1]
        if sorted_candidates:
            max_s = max(c["rerank_score"] for c in sorted_candidates)
            min_s = min(c["rerank_score"] for c in sorted_candidates)
            denom = max(max_s - min_s, 1e-9)
            for c in sorted_candidates:
                c["score"] = float((c["rerank_score"] - min_s) / denom)
        return sorted_candidates
