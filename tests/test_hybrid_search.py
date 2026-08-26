"""Tests for the hybrid search RRF fusion."""

from app.core.hybrid_search import HybridSearch


class _FakeVectorStore:
    def __init__(self, results):
        self.results = results

    def query(self, collection, query_embedding, top_k=20, where=None):
        return self.results[:top_k]


class _FakeBM25Store:
    def __init__(self, results):
        self.results = results

    def query(self, query_text, top_k=20):
        return self.results[:top_k]


def test_rrf_fuses_two_rankings():
    vec = [
        {"id": "a", "text": "alpha", "metadata": {}, "score": 0.9},
        {"id": "b", "text": "beta", "metadata": {}, "score": 0.8},
        {"id": "c", "text": "gamma", "metadata": {}, "score": 0.7},
    ]
    bm = [
        {"id": "b", "text": "beta", "metadata": {}, "score": 0.95},
        {"id": "d", "text": "delta", "metadata": {}, "score": 0.85},
        {"id": "a", "text": "alpha", "metadata": {}, "score": 0.5},
    ]
    hs = HybridSearch(_FakeVectorStore(vec), _FakeBM25Store(bm), rrf_k=60)
    fused = hs._rrf_fusion(vec, bm)
    ids = [r["id"] for r in fused]
    # All 4 unique docs present
    assert set(ids) == {"a", "b", "c", "d"}
    # b is in both → highest rrf score (rank 2 vec + rank 1 bm)
    assert ids[0] == "b"
    # a is in both → high score (rank 1 vec + rank 3 bm)
    assert ids[1] == "a"
    # c only in vec, d only in bm
    assert set(ids[2:]) == {"c", "d"}
    # Source marker for hybrid docs
    hybrid = [r for r in fused if r["id"] in {"a", "b"}]
    for h in hybrid:
        assert h["source_retriever"] == "hybrid"


def test_rrf_handles_one_empty():
    hs = HybridSearch(_FakeVectorStore([]), _FakeBM25Store([
        {"id": "x", "text": "x", "metadata": {}, "score": 0.5}
    ]), rrf_k=60)
    fused = hs._rrf_fusion([], [{"id": "x", "text": "x", "metadata": {}, "score": 0.5}])
    assert len(fused) == 1
    assert fused[0]["id"] == "x"
