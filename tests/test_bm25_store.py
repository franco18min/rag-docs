"""BM25 persistence and per-collection isolation (no embedding models)."""

from app.core.bm25_store import BM25Store


def test_bm25_persist_reload_and_collection_isolation(tmp_path):
    persist = str(tmp_path / "bm25.pkl")
    store = BM25Store(persist_path=persist)
    n = store.index(
        [
            {
                "id": "spark-1",
                "text": "Apache Spark SQL catalyst optimizer",
                "metadata": {"source": "spark.md"},
            }
        ],
        collection="col_a",
    )
    assert n == 1
    store.index(
        [
            {
                "id": "delta-1",
                "text": "Delta Lake ACID transactions",
                "metadata": {"source": "delta.md"},
            }
        ],
        collection="col_b",
    )

    reloaded = BM25Store(persist_path=persist)
    hits_a = reloaded.query("Spark SQL catalyst", top_k=5, collection="col_a")
    assert hits_a
    assert hits_a[0]["id"] == "spark-1"
    assert all(h["id"] != "delta-1" for h in hits_a)

    hits_b = reloaded.query("Delta Lake ACID", top_k=5, collection="col_b")
    assert hits_b
    assert hits_b[0]["id"] == "delta-1"
    assert all(h["id"] != "spark-1" for h in hits_b)

    missing = reloaded.query("Spark", collection="col_missing")
    assert missing == []
