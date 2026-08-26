"""End-to-end test of the RAG pipeline with mocked components.

These tests do NOT need GOOGLE_API_KEY, BGE-M3 downloads, or any external
service. They wire fake stores into the pipeline and verify orchestration.
"""
import numpy as np
import pytest

from app.core.bm25_store import BM25Store
from app.core.chunker import Chunker
from app.core.embedder import Embedder
from app.core.pipeline import RAGPipeline
from app.core.reranker import Reranker
from app.core.vector_store import VectorStore


class _StubEmbedder:
    """Returns deterministic embeddings of the right dim."""
    dim = 8

    def embed(self, texts, batch_size=32, normalize=True, show_progress=False):
        # Random but deterministic per text
        rng = np.random.default_rng(seed=hash(tuple(texts)) & 0xFFFFFFFF)
        return rng.random((len(texts), self.dim), dtype=np.float32)

    def embed_query(self, q):
        rng = np.random.default_rng(seed=hash(q) & 0xFFFFFFFF)
        return rng.random(self.dim, dtype=np.float32)


class _StubReranker:
    """Returns candidates in same order with synthetic rerank scores."""
    def rerank(self, query, candidates, top_k=None):
        for i, c in enumerate(candidates):
            c["rerank_score"] = 1.0 - i * 0.1
        return candidates[:top_k] if top_k else candidates


class _StubGenerator:
    model_name = "stub-model"

    def generate(self, question, context_chunks):
        return f"Stub answer to '{question}' using {len(context_chunks)} chunks"


def test_ingest_indexes_documents(tmp_path):
    pipeline = RAGPipeline(
        embedder=_StubEmbedder(),
        vector_store=VectorStore(persist_dir=str(tmp_path / "chroma")),
        bm25_store=BM25Store(persist_path=str(tmp_path / "bm25.pkl")),
        reranker=_StubReranker(),
        chunker=Chunker(chunk_size=64, chunk_overlap=8),
    )
    pipeline._generator = _StubGenerator()  # skip API-key check
    docs = [
        {"content": "Apache Spark is a unified analytics engine. " * 30, "source": "spark.md"},
        {"content": "Delta Lake brings ACID to data lakes. " * 30, "source": "delta.md"},
    ]
    stats = pipeline.ingest(docs, collection="test", rebuild=True, show_progress=False)
    assert stats["documents_loaded"] == 2
    assert stats["chunks_created"] > 2
    assert "test" in pipeline.collections()


def test_query_returns_answer_with_citations(tmp_path):
    pipeline = RAGPipeline(
        embedder=_StubEmbedder(),
        vector_store=VectorStore(persist_dir=str(tmp_path / "chroma")),
        bm25_store=BM25Store(persist_path=str(tmp_path / "bm25.pkl")),
        reranker=_StubReranker(),
        chunker=Chunker(chunk_size=64, chunk_overlap=8),
    )
    pipeline._generator = _StubGenerator()
    docs = [
        {"content": "Spark supports batch and streaming workloads. " * 20, "source": "spark.md"},
        {"content": "Delta Lake provides ACID transactions. " * 20, "source": "delta.md"},
    ]
    pipeline.ingest(docs, collection="test", rebuild=True, show_progress=False)

    result = pipeline.query("What is Spark?", collection="test", top_k=3)
    assert "answer" in result
    assert "citations" in result
    assert len(result["citations"]) <= 3
    assert result["latency_ms"] >= 0
    assert result["collection"] == "test"


def test_pipeline_query_with_no_chunks_in_collection(tmp_path):
    pipeline = RAGPipeline(
        embedder=_StubEmbedder(),
        vector_store=VectorStore(persist_dir=str(tmp_path / "chroma")),
        bm25_store=BM25Store(persist_path=str(tmp_path / "bm25.pkl")),
        reranker=_StubReranker(),
        chunker=Chunker(chunk_size=64, chunk_overlap=8),
    )
    pipeline._generator = _StubGenerator()
    result = pipeline.query("Anything", collection="empty", top_k=3)
    # No context → generator should still return something coherent
    assert "answer" in result
    assert result["citations"] == []
