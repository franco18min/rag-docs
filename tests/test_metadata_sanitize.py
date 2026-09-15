"""None metadata values must not reach Chroma; chunker drops them."""

from app.core.chunker import Chunker
from app.core.vector_store import _sanitize_metadatas


class _RecordingCollection:
    def __init__(self):
        self.upserts: list[dict] = []

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)
        for meta in kwargs.get("metadatas") or []:
            assert None not in meta.values()


class _StubVectorStore:
    """Stand-in for Chroma: records sanitized metadatas like VectorStore.add."""

    def __init__(self):
        self.collection = _RecordingCollection()

    def add(self, collection, ids, embeddings, documents, metadatas):
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=_sanitize_metadatas(metadatas),
        )


def test_sanitize_metadatas_drops_none():
    cleaned = _sanitize_metadatas([{"a": 1, "b": None, "c": "ok"}, None])  # type: ignore[list-item]
    assert cleaned == [{"a": 1, "c": "ok"}, {}]


def test_chunker_omits_none_metadata_fields():
    chunker = Chunker(chunk_size=64, chunk_overlap=8)
    chunks = chunker.chunk_text(
        "Spark SQL",
        source="spark.md",
        section=None,
        extra_metadata={"page": None, "lang": "en"},
    )
    assert len(chunks) == 1
    meta = chunks[0].metadata
    assert "section" not in meta
    assert "page" not in meta
    assert meta["lang"] == "en"
    assert None not in meta.values()


def test_stub_store_add_never_sends_none_metadata():
    store = _StubVectorStore()
    store.add(
        collection="c",
        ids=["1"],
        embeddings=[[0.1, 0.2]],
        documents=["text"],
        metadatas=[{"source": "a.md", "section": None, "page": 3}],
    )
    sent = store.collection.upserts[0]["metadatas"][0]
    assert sent == {"source": "a.md", "page": 3}
