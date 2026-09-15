"""
FastAPI app — RAG Docs API.

Endpoints:
    GET  /health         — health check + system info
    GET  /collections    — list available collections
    POST /query          — RAG query (the main endpoint)
    POST /ingest         — ingest documents from a server-side directory
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.core.generator import parse_citations
from app.core.pipeline import RAGPipeline
from app.models.query import IngestRequest, QueryRequest
from app.models.response import HealthResponse, IngestResponse, QueryResponse

# ---- Logging ----
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("rag-docs")


# ---- App ----
app = FastAPI(
    title="RAG Docs API",
    description="Sistema de preguntas y respuestas sobre documentación técnica",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Pipeline (lazy singleton) ----
_pipeline: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        logger.info("Initializing RAG pipeline (this loads models on first call)...")
        _pipeline = RAGPipeline()
    return _pipeline


# ---- Endpoints ----
@app.get("/health", response_model=HealthResponse)
async def health():
    try:
        pipeline = get_pipeline()
        collections = pipeline.collections()
    except Exception:
        logger.exception("Health check failed")
        return HealthResponse(
            status="degraded",
            version=__version__,
            model=settings.gemini_model,
            collections=[],
            embedding_model=settings.embedding_model,
            reranker_model=settings.reranker_model,
        )
    return HealthResponse(
        status="ok",
        version=__version__,
        model=settings.gemini_model,
        collections=collections,
        embedding_model=settings.embedding_model,
        reranker_model=settings.reranker_model,
    )


@app.get("/collections")
async def list_collections():
    """List the collections available in the vector store."""
    try:
        pipeline = get_pipeline()
        return {"collections": pipeline.collections()}
    except Exception as e:
        logger.exception("List collections failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Run a RAG query end-to-end."""
    try:
        pipeline = get_pipeline()
        result = pipeline.query(
            question=request.question,
            collection=request.collection,
            top_k=request.top_k,
        )
        chunks = result.get("chunks") or []
        if not request.include_citations:
            citations = []
        else:
            citations = parse_citations(result["answer"], chunks)
        return QueryResponse(
            answer=result["answer"],
            citations=citations,
            trace_id=None,  # Langfuse integration is optional; filled in observability/tracing.py
            latency_ms=result["latency_ms"],
            model=result["model"],
            collection=result["collection"],
            chunks_retrieved=len(result.get("chunks", [])),
        )
    except ValueError as e:
        # Missing API key etc.
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=f"Query failed: {e}") from e


@app.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    """Ingest documents from a server-side directory into a collection.

    Note: this endpoint is convenient for demos. In production, ingestion
    should be a separate batch process, not a request-time operation.
    """
    from app.core.loaders import load_documents  # local import to avoid heavy deps at startup

    source = Path(request.source_dir)
    if not source.exists() or not source.is_dir():
        raise HTTPException(status_code=400, detail=f"Directory not found: {request.source_dir}")

    try:
        documents = load_documents(str(source))
        if not documents:
            raise HTTPException(
                status_code=400,
                detail=f"No supported documents found in {request.source_dir}",
            )
        pipeline = get_pipeline()
        # Optional chunk size override
        if request.chunk_size or request.chunk_overlap:
            from app.core.chunker import Chunker
            pipeline.chunker = Chunker(
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
            )
        stats = pipeline.ingest(
            documents=documents,
            collection=request.collection,
            rebuild=request.rebuild,
        )
        return IngestResponse(collection=request.collection, **stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ingest failed")
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}") from e


# ---- Entry point ----
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", settings.api_host),
        port=int(os.getenv("API_PORT", settings.api_port)),
        reload=False,
        log_level=settings.log_level.lower(),
    )
