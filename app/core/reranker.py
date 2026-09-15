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

from app.config import settings


def _hybrid_slice(candidates: list[dict], top_k: int | None) -> list[dict]:
    """Keep hybrid fusion order. Never slice to an empty list when candidates exist."""
    if not candidates:
        return []
    k = settings.top_k_rerank if top_k is None else top_k
    if k is None or k <= 0:
        return list(candidates)
    return candidates[: min(k, len(candidates))]


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
        self._model = None
        self._initialized = True

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        return self._model

    def _should_skip_cross_encoder(self, top_k: int | None) -> bool:
        if not settings.enable_rerank:
            return True
        k = settings.top_k_rerank if top_k is None else top_k
        return k is None or k <= 0

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

        When rerank is disabled or ``top_k`` / ``TOP_K_RERANK`` is 0, the
        hybrid ranking is returned (never an empty slice of a non-empty list).

        Args:
            query: The query string.
            candidates: List of candidate dicts from hybrid search.
            top_k: Number of results to return. Defaults to settings.top_k_rerank.
        """
        if not candidates:
            return []

        if self._should_skip_cross_encoder(top_k):
            return _hybrid_slice(candidates, top_k)

        k = settings.top_k_rerank if top_k is None else top_k
        k = min(k, len(candidates))

        pairs = [(query, c.get("text", "")) for c in candidates]
        raw_scores = self._get_model().predict(pairs, show_progress_bar=False)

        # Attach scores and sort
        for c, s in zip(candidates, raw_scores, strict=False):
            c["rerank_score"] = float(s)

        sorted_candidates = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)[:k]

        # Normalize rerank scores in [0, 1]
        if sorted_candidates:
            max_s = max(c["rerank_score"] for c in sorted_candidates)
            min_s = min(c["rerank_score"] for c in sorted_candidates)
            denom = max(max_s - min_s, 1e-9)
            for c in sorted_candidates:
                c["score"] = float((c["rerank_score"] - min_s) / denom)
        return sorted_candidates
