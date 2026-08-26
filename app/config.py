"""
Centralized configuration for RAG Docs.

All settings are loaded from environment variables (or .env file) and exposed
via a single `settings` instance. Use `get_settings()` if you need to override
in tests.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # ===== LLM =====
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash-exp", alias="GEMINI_MODEL")

    # ===== Embeddings & Reranking =====
    embedding_model: str = Field(default="BAAI/bge-m3", alias="EMBEDDING_MODEL")
    reranker_model: str = Field(default="BAAI/bge-reranker-base", alias="RERANKER_MODEL")

    # ===== Vector Store =====
    vector_store_backend: str = Field(default="chroma", alias="VECTOR_STORE_BACKEND")
    chroma_persist_dir: str = Field(default="./data/chroma", alias="CHROMA_PERSIST_DIR")
    collection_name: str = Field(default="spark_docs", alias="COLLECTION_NAME")
    bm25_persist_path: str = Field(default="./data/bm25_index.pkl", alias="BM25_PERSIST_PATH")

    # ===== Databricks (when vector_store_backend="databricks") =====
    databricks_host: str = Field(default="", alias="DATABRICKS_HOST")
    databricks_token: str = Field(default="", alias="DATABRICKS_TOKEN")
    databricks_catalog: str = Field(default="rag_docs", alias="DATABRICKS_CATALOG")
    databricks_schema: str = Field(default="production", alias="DATABRICKS_SCHEMA")
    databricks_vector_endpoint: str = Field(
        default="rag_docs_endpoint", alias="DATABRICKS_VECTOR_ENDPOINT"
    )

    # ===== Chunking =====
    chunk_size: int = Field(default=512, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=64, alias="CHUNK_OVERLAP")

    # ===== Retrieval =====
    top_k_vector: int = Field(default=20, alias="TOP_K_VECTOR")
    top_k_bm25: int = Field(default=20, alias="TOP_K_BM25")
    top_k_rerank: int = Field(default=5, alias="TOP_K_RERANK")
    rrf_k: int = Field(default=60, alias="RRF_K")

    # ===== API =====
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # ===== Langfuse (optional) =====
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="http://localhost:3000", alias="LANGFUSE_HOST")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def has_langfuse(self) -> bool:
        """Whether Langfuse credentials are configured."""
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    def has_gemini(self) -> bool:
        """Whether the Gemini API key is configured."""
        return bool(self.google_api_key)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Module-level singleton for convenience
settings = get_settings()
