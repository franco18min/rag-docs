"""
Vector store factory.

Selects between Chroma (local dev) and Databricks Vector Search (production
deploy) based on ``settings.vector_store_backend``. Both backends expose the
same ``add`` / ``query`` / ``list_collections`` API, so the rest of the
pipeline is backend-agnostic.
"""

from __future__ import annotations

from typing import Literal

from app.config import settings
from app.core.vector_store import VectorStore


def get_vector_store():
    """Return a vector store instance for the configured backend."""
    backend: Literal["chroma", "databricks"] = settings.vector_store_backend

    if backend == "databricks":
        # Imported lazily so Chroma-only dev installs do not need the
        # databricks SDK at import time.
        from app.core.vector_store_databricks import DatabricksVectorStore

        return DatabricksVectorStore()

    return VectorStore()
