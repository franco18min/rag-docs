"""
End-to-end RAG pipeline.

Encapsulates the full flow:
    load → chunk → embed → index (vector + BM25) → hybrid search → re-rank → generate

Provides a single class that the API, the Streamlit UI, and the evaluation
scripts can all share.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from app.config import settings
from app.core.bm25_store import BM25Store
from app.core.chunker import Chunker
from app.core.embedder import Embedder
from app.core.generator import Generator
from app.core.hybrid_search import HybridSearch
from app.core.reranker import Reranker
from app.core.store_factory import get_vector_store
from app.core.vector_store import VectorStore


logger = logging.getLogger(__name__)


class RAGPipeline:
    """Orchestrates chunking, indexing, retrieval, re-ranking, and generation."""

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        vector_store: Optional[VectorStore] = None,
        bm25_store: Optional[BM25Store] = None,
        reranker: Optional[Reranker] = None,
        generator: Optional[Generator] = None,
        chunker: Optional[Chunker] = None,
    ):
        # Lazy-loaded, expensive objects are passed in so we can mock in tests
        self.embedder = embedder or Embedder()
        # Use the factory so the backend is selected from
        # ``settings.vector_store_backend`` ("chroma" or "databricks").
        self.vector_store = vector_store or get_vector_store()
        self.bm25_store = bm25_store or BM25Store()
        self.reranker = reranker or Reranker()
        # Generator requires API key — only build it lazily so the API can
        # still start (and ingestion works) without a key.
        self._generator: Optional[Generator] = generator
        self.chunker = chunker or Chunker()
        self.hybrid_search = HybridSearch(self.vector_store, self.bm25_store)

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------
    def ingest(
        self,
        documents: list[dict],
        collection: str,
        rebuild: bool = False,
        show_progress: bool = True,
    ) -> dict:
        """Load documents into the vector + BM25 stores.

        Args:
            documents: List of dicts with ``content`` and ``source`` keys.
            collection: Target collection name.
            rebuild: If True, delete the collection first.
            show_progress: Log progress.

        Returns:
            Dict with stats: documents_loaded, chunks_created, duration_seconds.
        """
        start = time.time()
        if rebuild:
            try:
                self.vector_store.delete_collection(collection)
            except Exception:
                pass

        if show_progress:
            logger.info("Chunking %d documents...", len(documents))
        chunk_dicts = self.chunker.chunk_documents(documents)
        # Convert dataclass to dict
        chunk_dicts = [
            {"id": c.chunk_id, "text": c.text, "metadata": c.metadata}
            for c in chunk_dicts
        ]

        if not chunk_dicts:
            return {
                "documents_loaded": len(documents),
                "chunks_created": 0,
                "duration_seconds": time.time() - start,
            }

        if show_progress:
            logger.info("Embedding %d chunks...", len(chunk_dicts))
        embeddings = self.embedder.embed(
            [c["text"] for c in chunk_dicts],
            batch_size=32,
            show_progress=show_progress,
        )

        if show_progress:
            logger.info("Indexing in Chroma...")
        self.vector_store.add(
            collection=collection,
            ids=[c["id"] for c in chunk_dicts],
            embeddings=embeddings.tolist(),
            documents=[c["text"] for c in chunk_dicts],
            metadatas=[c["metadata"] for c in chunk_dicts],
        )

        if show_progress:
            logger.info("Building BM25 index...")
        self.bm25_store.index(chunk_dicts, collection=collection)

        duration = time.time() - start
        if show_progress:
            logger.info(
                "Ingested %d chunks from %d documents in %.2fs",
                len(chunk_dicts), len(documents), duration,
            )
        return {
            "documents_loaded": len(documents),
            "chunks_created": len(chunk_dicts),
            "duration_seconds": duration,
        }

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def query(
        self,
        question: str,
        collection: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> dict:
        """End-to-end query: embed → hybrid search → rerank → generate.

        Returns a dict with keys: answer, citations, chunks, latency_ms, model, collection.
        """
        start = time.time()
        coll = collection or settings.collection_name
        top_k = top_k or settings.top_k_rerank

        # 1. Embed the query
        query_embedding = self.embedder.embed_query(question).tolist()

        # 2. Hybrid retrieval (top_k_vector + top_k_bm25 candidates)
        candidates = self.hybrid_search.search(
            collection=coll,
            query=question,
            query_embedding=query_embedding,
            top_k_vector=settings.top_k_vector,
            top_k_bm25=settings.top_k_bm25,
        )

        # 3. Re-rank → top_k
        reranked = self.reranker.rerank(question, candidates, top_k=top_k)

        # 4. Generate answer
        generator = self._get_generator()
        answer = generator.generate(question, reranked)

        # 5. Format citations
        citations = [
            {
                "source": c.get("metadata", {}).get("source", "unknown"),
                "section": c.get("metadata", {}).get("section"),
                "page": c.get("metadata", {}).get("page"),
                "chunk_index": c.get("metadata", {}).get("chunk_index"),
                "text_snippet": (c.get("text", "") or "")[:280],
                "score": float(c.get("score", 0.0)),
            }
            for c in reranked
        ]

        latency_ms = (time.time() - start) * 1000
        return {
            "answer": answer,
            "citations": citations,
            "chunks": reranked,
            "latency_ms": latency_ms,
            "model": settings.gemini_model,
            "collection": coll,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_generator(self) -> Generator:
        if self._generator is None:
            self._generator = Generator()
        return self._generator

    def collections(self) -> list[str]:
        return self.vector_store.list_collections()

    def collection_count(self, name: str) -> int:
        return self.vector_store.collection_count(name)
