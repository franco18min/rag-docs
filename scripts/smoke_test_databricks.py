"""Smoke test: create Delta table + Vector Search index, ingest 5 dummy
chunks, query, and print the top result. Run from project root with the venv
activated:

    python scripts/smoke_test_databricks.py

End-to-end validation of the Databricks Vector Search adapter. The test:

    1. Creates the Delta table + Vector Search index on the configured endpoint
    2. Inserts 5 rows of dummy chunks with 4-dim unit vectors
    3. Waits for the index to provision and sync (this takes 2-5 minutes the
       first time the endpoint serves a new index — subsequent runs are
       faster)
    4. Queries the index and validates that the top result is the expected
       closest document
    5. Cleans up the index and Delta table
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Ensure the project root is on the import path when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env BEFORE importing the Databricks client. The legacy
# VectorSearchClient init calls ``mlflow.utils.databricks_utils
# .get_databricks_host_creds()`` which reads DATABRICKS_HOST/TOKEN env vars
# directly, ignoring Pydantic settings.
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Force the Databricks backend regardless of what the .env says
os.environ["VECTOR_STORE_BACKEND"] = "databricks"

from databricks.sdk import WorkspaceClient  # noqa: E402

from app.core.vector_store_databricks import DatabricksVectorStore  # noqa: E402

# How long to wait for the Vector Search index to become ``ready=True``.
# First-time provisioning of a STANDARD endpoint can take 2-5 minutes; the
# state machine goes PROVISIONING_ENDPOINT -> PROVISIONING_INDEX ->
# PROVISIONING_PIPELINE_RESOURCES -> PROVISIONING_INITIAL_SNAPSHOT ->
# ONLINE_TRIGGERED_UPDATE.
PROVISIONING_TIMEOUT_S = 10 * 60
PROVISIONING_POLL_S = 15


def _wait_for_index_ready(
    ws_token: str, endpoint: str, index_name: str, *, timeout_s: int = PROVISIONING_TIMEOUT_S
) -> bool:
    """Poll ``describe()`` until the index reports ``ready=True``.

    Returns True if the index became ready before ``timeout_s`` elapsed, else
    False. The caller can then decide whether to fail the test or to skip the
    query step.
    """
    from databricks.ai_search.client import AISearchClient  # local import

    client = AISearchClient()
    deadline = time.time() + timeout_s
    last_state = None
    while time.time() < deadline:
        try:
            idx = client.get_index(endpoint_name=endpoint, index_name=index_name)
            desc = idx.describe()
            status = (desc or {}).get("status", {}) or {}
            state = status.get("detailed_state", "?")
            ready = status.get("ready", False)
            indexed = status.get("indexed_row_count", "?")
        except Exception as e:
            state, ready, indexed = f"err:{type(e).__name__}", False, "?"
        if state != last_state:
            print(f"    index state: {state}  ready={ready}  indexed={indexed}")
            last_state = state
        if ready:
            return True
        time.sleep(PROVISIONING_POLL_S)
    return False


def main() -> int:
    s = DatabricksVectorStore()
    index_name = s._index_name("smoke_test")  # noqa: SLF001 — internal helper
    table = s._table_name("smoke_test")  # noqa: SLF001

    # 1. Create Delta table + Vector Search index
    print(f"\n[1/4] Creating index on {s.endpoint} ...")
    s.create_index_from_table(collection="smoke_test", embedding_dim=4)
    print("    OK Delta table + index ready (provisioning will happen async)")

    # 2. Ingest 5 dummy chunks with 4-dim embeddings
    print("\n[2/4] Ingesting 5 dummy chunks ...")
    ids = [f"smoke-{i}" for i in range(5)]
    docs = [
        "Delta Lake is an open-source storage format",
        "Vector Search indexes embeddings for similarity",
        "Databricks Free Edition supports Vector Search in beta",
        "BGE-M3 is a multilingual embedding model from BAAI",
        "Reciprocal Rank Fusion combines ranked lists",
    ]
    metas = [{"source": "doc1", "chunk_index": i} for i in range(5)]
    # 4-dim unit vectors; chunk 0 and chunk 1 are similar (close to [1,0,0,0])
    embs = [
        [1.0, 0.1, 0.0, 0.0],
        [0.95, 0.15, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    s.add("smoke_test", ids=ids, embeddings=embs, documents=docs, metadatas=metas)
    print(f"    OK ingested {len(ids)} rows into {table}")

    # 2b. Wait for the index to fully provision + sync. First-time creation
    # of an index on a STANDARD endpoint can take 2-5 minutes; the SDK does
    # not block, so we poll until ready=True or timeout.
    print("\n[2b] Waiting for index to become ready (this can take 2-5 min) ...")
    if not _wait_for_index_ready(s.token, s.endpoint, index_name):
        print(f"    TIMEOUT after {PROVISIONING_TIMEOUT_S}s waiting for {index_name}")
        print("    (The index is still provisioning in the background; you can")
        print("     re-run this script to retry the query once it's online.)")
        # Cleanup and bail — we don't want to leave the index orphaned.
        _cleanup(s, index_name, table)
        return 1

    # 3. Query — should match the two "delta-like" vectors.
    print("\n[3/4] Querying with [0.98, 0.05, 0.0, 0.0] ...")
    print("    (expecting 'Delta Lake...' at top, then 'Vector Search...')")
    results = s.query("smoke_test", query_embedding=[0.98, 0.05, 0.0, 0.0], top_k=3)
    if not results:
        print("    FAIL no results returned")
        _cleanup(s, index_name, table)
        return 1

    for i, r in enumerate(results, 1):
        print(f"    [{i}] score={r['score']:.3f}  text={r['text'][:60]!r}")

    # Validate the top result is what we expect (closest to [1, 0, 0, 0]).
    if "Delta Lake" not in results[0]["text"]:
        print("    FAIL top result is not 'Delta Lake' — ranking looks wrong")
        _cleanup(s, index_name, table)
        return 1
    print("    OK top result is the expected closest document")

    # 4. Cleanup
    print("\n[4/4] Cleaning up index + table ...")
    _cleanup(s, index_name, table)
    print("    OK done")
    return 0


def _cleanup(s: DatabricksVectorStore, index_name: str, table: str) -> None:
    """Drop the Vector Search index and the underlying Delta table."""
    try:
        s.delete_collection("smoke_test")
        print(f"    deleted index {index_name}")
    except Exception as e:
        print(f"    WARN could not delete index: {e}")
    try:
        ws = WorkspaceClient(host=s.host, token=s.token)
        ws.api_client.do(
            "DELETE",
            f"/api/2.1/unity-catalog/tables/{table}",
            headers={"Authorization": f"Bearer {s.token}"},
        )
        print(f"    deleted table {table}")
    except Exception as e:
        print(f"    WARN could not delete table: {e}")


if __name__ == "__main__":
    raise SystemExit(main())
