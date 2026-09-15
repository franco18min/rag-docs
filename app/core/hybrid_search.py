"""
Hybrid search with Reciprocal Rank Fusion (RRF).

Fuses rankings from dense vector search and BM25 keyword search. RRF is a
simple, well-studied rank-aggregation method that doesn't require score
calibration across the two retrievers.

Reference: Cormack et al., "Reciprocal Rank Fusion outperforms Condorcet and
individual Rank Learning Methods", SIGIR 2009.
"""
from __future__ import annotations

from app.config import settings
from app.core.bm25_store import BM25Store
from app.core.vector_store import VectorStore


class HybridSearch:
    """Combine vector and BM25 retrieval with RRF."""

    def __init__(
        self,
        vector_store: VectorStore,
        bm25_store: BM25Store,
        rrf_k: int | None = None,
    ):
        self.vector_store = vector_store
        self.bm25_store = bm25_store
        self.rrf_k = rrf_k if rrf_k is not None else settings.rrf_k

    def search(
        self,
        collection: str,
        query: str,
        query_embedding: list[float],
        top_k_vector: int = 20,
        top_k_bm25: int = 20,
    ) -> list[dict]:
        """Run both retrievers and fuse results with RRF.

        Returns a list of dicts with keys: id, text, metadata, score, rrf_score,
        source_retriever. ``rrf_score`` is the fused score, ``score`` is the
        RRF score normalized to [0, 1] for display.
        """
        vec_results = self.vector_store.query(
            collection=collection,
            query_embedding=query_embedding,
            top_k=top_k_vector,
        )
        bm25_results = self.bm25_store.query(
            query, top_k=top_k_bm25, collection=collection
        )

        return self._rrf_fusion(vec_results, bm25_results)

    # ------------------------------------------------------------------
    # RRF
    # ------------------------------------------------------------------
    def _rrf_fusion(
        self,
        vec_results: list[dict],
        bm25_results: list[dict],
    ) -> list[dict]:
        """Reciprocal Rank Fusion over two ranked lists.

        RRF(d) = sum_{r in retrievers} 1 / (k + rank_r(d))

        where rank is 1-based. We sum contributions across the two retrievers
        so chunks retrieved by both get higher fused scores.
        """
        scores: dict[str, float] = {}
        # Map id -> original result (prefer vector's text since it has the
        # exact text used at index time)
        results_by_id: dict[str, dict] = {}

        for rank, r in enumerate(vec_results, start=1):
            doc_id = r["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (self.rrf_k + rank)
            results_by_id[doc_id] = r
            results_by_id[doc_id]["_vec_rank"] = rank

        for rank, r in enumerate(bm25_results, start=1):
            doc_id = r["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (self.rrf_k + rank)
            if doc_id not in results_by_id:
                results_by_id[doc_id] = r
            results_by_id[doc_id]["_bm25_rank"] = rank

        # Build fused list, sorted by RRF score desc
        fused = []
        for doc_id, rrf in scores.items():
            r = results_by_id[doc_id]
            r["rrf_score"] = rrf
            fused.append(r)
        fused.sort(key=lambda x: x["rrf_score"], reverse=True)

        # Normalize RRF scores to [0, 1] for nicer display / reranking input
        if fused:
            max_s = fused[0]["rrf_score"]
            for r in fused:
                r["score"] = r["rrf_score"] / max_s if max_s > 0 else 0.0

        # Mark dual-retrieval bonus
        for r in fused:
            r["source_retriever"] = (
                "hybrid" if "_vec_rank" in r and "_bm25_rank" in r else r.get("source_retriever", "unknown")
            )
        return fused
