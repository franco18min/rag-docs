"""Request schemas for the RAG API."""

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request to query the RAG system."""

    question: str = Field(..., min_length=1, description="The question to answer")
    collection: str | None = Field(
        default=None, description="Collection to query (defaults to configured collection)"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Final number of chunks to use for the answer")
    include_citations: bool = Field(
        default=True, description="Include source citations in the response"
    )


class IngestRequest(BaseModel):
    """Request to ingest documents from a directory."""

    source_dir: str = Field(..., description="Directory containing documents to ingest")
    collection: str = Field(..., description="Target collection name")
    chunk_size: int | None = Field(default=None, ge=64, le=4096)
    chunk_overlap: int | None = Field(default=None, ge=0, le=1024)
    rebuild: bool = Field(default=False, description="Drop and recreate the collection before ingesting")
