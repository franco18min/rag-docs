"""
Text chunking with sliding window strategy.

Token-aware chunking using tiktoken (cl100k_base) so chunks respect the
embedding model's tokenizer. Each chunk carries rich metadata so retrieval
can filter and re-rank accurately.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

import tiktoken

from app.config import settings


@dataclass
class Chunk:
    """A chunk of text with metadata."""

    text: str
    chunk_id: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"text": self.text, "chunk_id": self.chunk_id, "metadata": self.metadata}


class Chunker:
    """Sliding window chunker using tiktoken for token-aware splitting."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        encoding_name: str = "cl100k_base",
    ):
        if chunk_size is not None and chunk_overlap is not None and chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.encoding = tiktoken.get_encoding(encoding_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def chunk_text(
        self,
        text: str,
        source: str,
        section: str | None = None,
        extra_metadata: dict | None = None,
    ) -> list[Chunk]:
        """Split text into chunks using a sliding window.

        Args:
            text: The text to chunk.
            source: Source identifier (file path or URL).
            section: Optional section/heading context.
            extra_metadata: Additional metadata to attach to every chunk.

        Returns:
            List of Chunk objects with stable IDs and metadata.
        """
        if not text or not text.strip():
            return []

        text = self._normalize(text)
        tokens = self.encoding.encode(text)

        if len(tokens) <= self.chunk_size:
            return [
                self._build_chunk(
                    text=text,
                    source=source,
                    section=section,
                    idx=0,
                    total=1,
                    start_token=0,
                    end_token=len(tokens),
                    extra=extra_metadata,
                )
            ]

        chunks: list[Chunk] = []
        stride = self.chunk_size - self.chunk_overlap
        start = 0
        idx = 0

        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens).strip()
            if chunk_text:
                chunks.append(
                    self._build_chunk(
                        text=chunk_text,
                        source=source,
                        section=section,
                        idx=idx,
                        total=-1,  # placeholder, updated below
                        start_token=start,
                        end_token=end,
                        extra=extra_metadata,
                    )
                )
                idx += 1
            if end == len(tokens):
                break
            start += stride

        # Patch total_chunks in metadata once we know the count
        for c in chunks:
            c.metadata["total_chunks"] = len(chunks)

        return chunks

    def chunk_documents(self, documents: list[dict]) -> list[Chunk]:
        """Chunk a list of documents.

        Each document must be a dict with at least ``content`` and ``source``.
        Optional keys: ``section`` and ``metadata`` (extra metadata).
        """
        all_chunks: list[Chunk] = []
        for doc in documents:
            chunks = self.chunk_text(
                text=doc.get("content", ""),
                source=doc.get("source", "unknown"),
                section=doc.get("section"),
                extra_metadata=doc.get("metadata"),
            )
            all_chunks.extend(chunks)
        return all_chunks

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _build_chunk(
        self,
        text: str,
        source: str,
        section: str | None,
        idx: int,
        total: int,
        start_token: int,
        end_token: int,
        extra: dict | None,
    ) -> Chunk:
        return Chunk(
            text=text,
            chunk_id=self._make_chunk_id(text, source, idx),
            metadata={
                "source": source,
                "section": section,
                "chunk_index": idx,
                "total_chunks": total,
                "start_token": start_token,
                "end_token": end_token,
                "num_tokens": end_token - start_token,
                **(extra or {}),
            },
        )

    @staticmethod
    def _make_chunk_id(text: str, source: str, index: int) -> str:
        """Deterministic chunk ID — same content + position always returns the same ID."""
        h = hashlib.sha256(f"{source}::{index}::{text[:200]}".encode()).hexdigest()[:16]
        return f"{h}_{index}"

    @staticmethod
    def _normalize(text: str) -> str:
        """Collapse excess whitespace while keeping paragraph structure."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
