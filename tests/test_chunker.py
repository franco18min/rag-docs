"""Tests for the sliding window chunker."""

import pytest

from app.core.chunker import Chunker


def test_short_text_single_chunk():
    c = Chunker(chunk_size=100, chunk_overlap=10)
    chunks = c.chunk_text("Hola mundo", source="doc1.md")
    assert len(chunks) == 1
    assert chunks[0].metadata["total_chunks"] == 1
    assert chunks[0].metadata["source"] == "doc1.md"


def test_empty_text_returns_empty_list():
    c = Chunker()
    assert c.chunk_text("", source="x") == []
    assert c.chunk_text("   \n  ", source="x") == []


def test_long_text_produces_overlapping_chunks():
    text = "Lorem ipsum dolor sit amet. " * 200  # ~1000 tokens worth
    c = Chunker(chunk_size=128, chunk_overlap=16)
    chunks = c.chunk_text(text, source="doc1.md")
    assert len(chunks) > 1
    # Every chunk has total_chunks set
    for chunk in chunks:
        assert chunk.metadata["total_chunks"] == len(chunks)
        assert chunk.metadata["chunk_index"] >= 0


def test_chunk_ids_are_deterministic():
    c = Chunker(chunk_size=64, chunk_overlap=8)
    text = "Spark is a unified analytics engine. " * 20
    a = c.chunk_text(text, source="x")
    b = c.chunk_text(text, source="x")
    assert [ch.chunk_id for ch in a] == [ch.chunk_id for ch in b]


def test_chunk_documents_batches_sources():
    c = Chunker(chunk_size=64, chunk_overlap=8)
    docs = [
        {"content": "Foo bar baz " * 50, "source": "a.md"},
        {"content": "Hello world " * 50, "source": "b.md"},
    ]
    chunks = c.chunk_documents(docs)
    sources = {ch.metadata["source"] for ch in chunks}
    assert sources == {"a.md", "b.md"}


def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        Chunker(chunk_size=10, chunk_overlap=10)
    with pytest.raises(ValueError):
        Chunker(chunk_size=10, chunk_overlap=20)
