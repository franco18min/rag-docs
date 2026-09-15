"""FastAPI TestClient paths with a stubbed pipeline (no BGE / Gemini)."""

from fastapi.testclient import TestClient

import app.main as main_mod
from app.main import app


class _FakePipeline:
    def collections(self):
        return ["spark_docs"]

    def query(self, question, collection=None, top_k=None):
        chunks = [
            {
                "id": "c1",
                "text": "Spark SQL documentation.",
                "metadata": {"source": "spark.md", "section": "SQL"},
                "score": 0.91,
            }
        ]
        return {
            "answer": f"Stub: {question} [#1]",
            "citations": [],
            "chunks": chunks,
            "latency_ms": 1.5,
            "model": "stub-model",
            "collection": collection or "spark_docs",
        }


def test_health_does_not_load_bge(monkeypatch):
    main_mod._pipeline = None
    monkeypatch.setattr(main_mod, "get_pipeline", lambda: _FakePipeline())
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "spark_docs" in body["collections"]


def test_query_with_fake_pipeline(monkeypatch):
    main_mod._pipeline = None
    monkeypatch.setattr(main_mod, "get_pipeline", lambda: _FakePipeline())
    client = TestClient(app)
    response = client.post(
        "/query",
        json={"question": "What is Spark SQL?", "collection": "spark_docs", "top_k": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert "Stub:" in body["answer"]
    assert body["collection"] == "spark_docs"
    assert body["chunks_retrieved"] == 1
    assert body["citations"]
    assert body["citations"][0]["citation_number"] == 1
