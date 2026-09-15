"""
BM25 keyword search store.

Persisted to disk via pickle. Tokenization is intentionally simple (lowercase
+ split on non-alphanumerics) because the corpus is technical documentation
where exact terms (function names, config flags) matter more than morphology.
"""

from __future__ import annotations

import pickle
import re
from collections.abc import Iterable
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.config import settings

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


class BM25Store:
    """Wrapper around rank_bm25 with on-disk persistence."""

    def __init__(self, persist_path: str | None = None):
        self.persist_path = Path(persist_path or settings.bm25_persist_path).resolve()
        self.bm25: BM25Okapi | None = None
        self.docs: list[dict] = []  # each: {id, text, metadata}
        self._loaded = False
        self._collection: str | None = None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _persist_path_for(self, collection: str) -> Path:
        # Allow one BM25 index per collection in the future by namespacing
        return self.persist_path.with_name(
            f"{self.persist_path.stem}_{collection}{self.persist_path.suffix}"
        )

    def save(self, collection: str) -> None:
        path = self._persist_path_for(collection)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"bm25": self.bm25, "docs": self.docs}, f)

    def load(self, collection: str) -> bool:
        path = self._persist_path_for(collection)
        if not path.exists():
            self._loaded = False
            self._collection = None
            return False
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.bm25 = data["bm25"]
        self.docs = data["docs"]
        self._loaded = True
        self._collection = collection
        return True

    def is_loaded(self) -> bool:
        return self._loaded and self.bm25 is not None

    # ------------------------------------------------------------------
    # Build & update
    # ------------------------------------------------------------------
    def index(self, chunks: Iterable[dict], collection: str) -> int:
        """Build the index from a list of chunks.

        Each chunk is a dict: {id, text, metadata}.
        Returns the number of documents indexed.
        """
        chunks = list(chunks)
        if not chunks:
            self.bm25 = None
            self.docs = []
            self._loaded = True
            self._collection = collection
            self.save(collection)
            return 0

        tokenized_corpus = [_tokenize(c["text"]) for c in chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.docs = chunks
        self._loaded = True
        self._collection = collection
        self.save(collection)
        return len(chunks)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def query(
        self,
        query_text: str,
        top_k: int = 20,
        collection: str | None = None,
    ) -> list[dict]:
        """Return top-k most relevant chunks by BM25 score.

        Each result: {id, text, metadata, score, source_retriever}.
        If ``collection`` is set, load that collection's pickle when it is
        not already in memory.
        """
        if collection and self._collection != collection:
            if not self.load(collection):
                return []
        if not self.is_loaded() or not self.docs:
            return []

        tokens = _tokenize(query_text)
        scores = self.bm25.get_scores(tokens)

        # Get indices of top_k highest scores
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        # Normalize BM25 scores to [0, 1] using min-max
        top_scores = [scores[i] for i in top_indices]
        max_s = max(top_scores) if top_scores else 0.0
        min_s = min(top_scores) if top_scores else 0.0
        denom = max(max_s - min_s, 1e-9)

        results: list[dict] = []
        for idx, score in zip(top_indices, top_scores, strict=False):
            doc = self.docs[idx]
            results.append(
                {
                    "id": doc["id"],
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "score": float((score - min_s) / denom),
                    "raw_score": float(score),
                    "source_retriever": "bm25",
                }
            )
        return results

    def size(self) -> int:
        return len(self.docs) if self.docs else 0
