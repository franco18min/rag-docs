"""Response schemas for the RAG API."""
from typing import Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A citation to a source chunk used to generate the answer."""

    source: str = Field(..., description="Source file or document path")
    section: Optional[str] = Field(default=None, description="Section or heading, if available")
    page: Optional[int] = Field(default=None, description="Page number, if available")
    chunk_index: Optional[int] = Field(default=None, description="Index of the chunk within the document")
    text_snippet: str = Field(..., description="Short snippet of the cited text")
    score: float = Field(..., description="Relevance score (0-1)")


class QueryResponse(BaseModel):
    """Response from a RAG query."""

    answer: str = Field(..., description="Generated answer to the question")
    citations: list[Citation] = Field(default_factory=list, description="Source citations")
    trace_id: Optional[str] = Field(default=None, description="Observability trace ID, if available")
    latency_ms: float = Field(..., description="End-to-end latency in milliseconds")
    model: str = Field(..., description="LLM model used for generation")
    collection: str = Field(..., description="Collection queried")
    chunks_retrieved: int = Field(..., description="Number of chunks used to generate the answer")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    model: str
    collections: list[str] = Field(default_factory=list)
    embedding_model: str
    reranker_model: str


class IngestResponse(BaseModel):
    """Response from an ingestion run."""

    collection: str
    documents_loaded: int
    chunks_created: int
    duration_seconds: float
