"""
Document ingestion CLI.

Reads a directory of documents (PDF, Markdown, HTML, TXT), chunks them, embeds
the chunks, and indexes them in Chroma + BM25.

Usage:
    python -m scripts.ingest --source ./data/raw --collection spark_docs
    python -m scripts.ingest --source ./data/raw --collection spark_docs --rebuild
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from app.core.chunker import Chunker
from app.core.loaders import SUPPORTED_EXTENSIONS, load_documents
from app.core.pipeline import RAGPipeline

logger = logging.getLogger("ingest")


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into the RAG system")
    parser.add_argument("--source", required=True, help="Directory with documents to ingest")
    parser.add_argument("--collection", required=True, help="Target collection name")
    parser.add_argument("--chunk-size", type=int, default=None, help="Override CHUNK_SIZE")
    parser.add_argument("--chunk-overlap", type=int, default=None, help="Override CHUNK_OVERLAP")
    parser.add_argument(
        "--rebuild", action="store_true", help="Drop and recreate the collection first"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    start = time.time()
    print(f"📂 Loading documents from {args.source}...")
    print(f"   Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
    documents = load_documents(args.source)
    print(f"✅ {len(documents)} documents loaded")

    if not documents:
        print("⚠️  No supported documents found.")
        print(f"   Formatos soportados: {', '.join(SUPPORTED_EXTENSIONS)}")
        sys.exit(1)

    chunker = Chunker(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    pipeline = RAGPipeline(chunker=chunker)

    print(f"🚀 Ingesting into collection '{args.collection}' (rebuild={args.rebuild})...")
    stats = pipeline.ingest(
        documents=documents,
        collection=args.collection,
        rebuild=args.rebuild,
    )

    duration = time.time() - start
    print(
        f"🎉 Ingest complete: {stats['chunks_created']} chunks from "
        f"{stats['documents_loaded']} documents in {duration:.2f}s "
        f"({stats['chunks_created'] / max(duration, 1e-3):.1f} chunks/s)"
    )
    print(f"   Collection '{args.collection}' is ready for queries.")


if __name__ == "__main__":
    main()
