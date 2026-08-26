"""
Embeddings wrapper using sentence-transformers.

Singleton pattern because the model is expensive to load. The default model
(BAAI/bge-m3) supports multilingual and long-context retrieval, which fits
the use case of technical documentation in Spanish/English.
"""
from __future__ import annotations

import os
from typing import Optional

# Silence noisy HuggingFace progress bars and telemetry
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings


class Embedder:
    """Lazy-loaded singleton wrapper around sentence-transformers."""

    _instance: Optional["Embedder"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_name: Optional[str] = None):
        if getattr(self, "_initialized", False):
            return
        self.model_name = model_name or settings.embedding_model
        # trust_remote_code=True is required for bge-m3 which has custom code
        self.model = SentenceTransformer(self.model_name, trust_remote_code=True)
        self.dim = self.model.get_sentence_embedding_dimension()
        self._initialized = True

    def embed(
        self,
        texts: list[str],
        batch_size: int = 32,
        normalize: bool = True,
        show_progress: bool = False,
    ) -> np.ndarray:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of texts to embed.
            batch_size: Encoding batch size.
            normalize: L2-normalize embeddings (recommended for cosine similarity).
            show_progress: Show a tqdm bar.

        Returns:
            numpy array of shape (len(texts), dim). Empty array if input is empty.
        """
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
        )
        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string. Returns a 1-D array."""
        return self.embed([query], normalize=True)[0]

    @property
    def dimension(self) -> int:
        return self.dim
