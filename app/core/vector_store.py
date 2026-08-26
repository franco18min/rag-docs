"""
Chroma vector store wrapper.

Persistent client, per-collection index, cosine similarity on dense embeddings.
Stores chunks with metadata so retrieval can later filter on source, section,
or date.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings


class VectorStore:
    """Thin wrapper around Chroma for add/query/list operations."""

    def __init__(self, persist_dir: str | None = None):
        self.persist_dir = Path(persist_dir or settings.chroma_persist_dir).resolve()
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
        )

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------
    def get_or_create_collection(self, name: str):
        """Get or create a collection with cosine distance."""
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def list_collections(self) -> list[str]:
        return [c.name for c in self.client.list_collections()]

    def delete_collection(self, name: str) -> None:
        self.client.delete_collection(name)

    def collection_count(self, name: str) -> int:
        try:
            return self.client.get_collection(name).count()
        except Exception:
            return 0

    def reset_persist_dir(self) -> None:
        """Dangerous: wipe the entire vector store on disk."""
        if self.persist_dir.exists():
            shutil.rmtree(self.persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------
    def add(
        self,
        collection: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Add or update chunks in a collection."""
        if not ids:
            return
        coll = self.get_or_create_collection(collection)
        coll.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def query(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 20,
        where: dict | None = None,
    ) -> list[dict]:
        """Return top-k most similar chunks.

        Each result is a dict with keys: ``id``, ``text``, ``metadata``, ``score``.
        ``score`` is converted to cosine similarity in [0, 1] (1 = identical).
        """
        coll = self.get_or_create_collection(collection)
        if coll.count() == 0:
            return []

        result = coll.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]

        out: list[dict] = []
        for i, _id in enumerate(ids):
            distance = dists[i] if i < len(dists) else 0.0
            # Cosine distance in [0, 2] → similarity in [-1, 1]. With normalized
            # embeddings from BGE, distance is in [0, 2] and similarity in [-1, 1].
            # We clip to [0, 1] for downstream display.
            score = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
            out.append(
                {
                    "id": _id,
                    "text": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "score": score,
                    "source_retriever": "vector",
                }
            )
        return out
