"""
Databricks Vector Search adapter.

Implements the same interface as ``app.core.vector_store.VectorStore`` but
backed by a Delta table + Databricks Vector Search index. Used for production
deployment on Databricks (Free Edition or higher).

Design notes:
    - Embeddings are pre-computed by the local BGE-M3 model (1024 dims) and
      written to a Delta table column. The Vector Search index is configured
      with ``embedding_dimension=1024`` and ``embedding_source_column="embedding"``
      so the index uses our embeddings, not Databricks' managed embedder.
    - The Delta table is the source of truth. The index is a queryable
      projection that can be rebuilt from the table. We ``sync()`` the
      index after each ingestion batch.
    - The ``list_collections`` / ``delete_collection`` methods map to
      index lifecycle on the Vector Search endpoint.
"""
from __future__ import annotations

import logging
from typing import Optional

from databricks.sdk import WorkspaceClient

# Databricks rebranded Vector Search to "AI Search" in 2025. The backend
# now treats STANDARD Vector Search endpoints as AI Search endpoints and
# rejects create_index calls that don't go through ``AISearchClient``.
# The ``databricks-vectorsearch`` package is now a thin re-export of
# ``databricks-ai-search``; we import the new client directly.
from databricks.ai_search.client import AISearchClient

from app.config import settings

logger = logging.getLogger(__name__)


class DatabricksVectorStore:
    """Adapter exposing the same API as ``VectorStore`` but on Databricks."""

    def __init__(
        self,
        host: Optional[str] = None,
        token: Optional[str] = None,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        self.host = host or settings.databricks_host
        self.token = token or settings.databricks_token
        self.catalog = catalog or settings.databricks_catalog
        self.schema = schema or settings.databricks_schema
        self.endpoint = endpoint or settings.databricks_vector_endpoint

        if not all([self.host, self.token, self.catalog, self.schema, self.endpoint]):
            raise ValueError(
                "Missing required Databricks settings: host, token, catalog, schema, endpoint"
            )

        # Two clients: WorkspaceClient for SQL/Delta operations, AISearchClient
        # for the index. The current SDK uses ``workspace_url`` and
        # ``personal_access_token`` parameter names.
        self.ws = WorkspaceClient(host=self.host, token=self.token)
        self.vsc = AISearchClient(workspace_url=self.host, personal_access_token=self.token)

    # ------------------------------------------------------------------
    # Index / collection naming
    # ------------------------------------------------------------------
    def _index_name(self, collection: str) -> str:
        """Map a Chroma-style collection name to a Vector Search index name.

        Unity Catalog requires unique names across tables and indexes, so
        we append ``_idx`` to keep the index distinct from the underlying
        Delta table. Vector Search index names must be fully qualified
        ``<catalog>.<schema>.<index>`` with only alphanumerics/underscores.
        """
        safe = collection.replace("-", "_").replace(".", "_")
        return f"{self.catalog}.{self.schema}.{safe}_idx"

    def _table_name(self, collection: str) -> str:
        return f"{self.catalog}.{self.schema}.{collection}"

    # ------------------------------------------------------------------
    # Collection / index management
    # ------------------------------------------------------------------
    def get_or_create_collection(self, name: str):
        """For Databricks, the 'collection' is a Vector Search index.

        This method is provided for API parity with the Chroma wrapper but
        does not actually create the index (that requires the Delta table to
        exist). Use ``create_index_from_table`` for that.
        """
        index_name = self._index_name(name)
        try:
            index = self.vsc.get_index(endpoint_name=self.endpoint, index_name=index_name)
            logger.info(f"Found existing index: {index_name}")
            return index
        except Exception as e:
            logger.info(f"Index {index_name} does not exist yet: {e}")
            return None

    def list_collections(self) -> list[str]:
        """List Vector Search index names on the configured endpoint."""
        try:
            # AISearchClient.list_indexes uses ``name=`` (not
            # ``endpoint_name=``) and returns a dict whose key is
            # ``vector_indexes`` (NOT ``vector_search_indexes`` as the
            # legacy API used). Be defensive about both keys for back-compat.
            res = self.vsc.list_indexes(name=self.endpoint)
            if isinstance(res, list):
                items = res
            elif isinstance(res, dict):
                items = (
                    res.get("vector_indexes")
                    or res.get("vector_search_indexes")
                    or res.get("indexes")
                    or []
                )
            else:
                items = []
            return [getattr(idx, "name", None) or idx.get("name", "?") for idx in items]
        except Exception as e:
            logger.warning(f"Failed to list indexes: {e}")
            return []

    def delete_collection(self, name: str) -> None:
        index_name = self._index_name(name)
        try:
            self.vsc.delete_index(endpoint_name=self.endpoint, index_name=index_name)
            logger.info(f"Deleted index {index_name}")
        except Exception as e:
            logger.warning(f"Failed to delete index {index_name}: {e}")

    def collection_count(self, name: str) -> int:
        """Return the row count of the underlying Delta table."""
        table = self._table_name(name)
        try:
            result = self.ws.statement_execution.execute_statement(
                warehouse_id=self._warehouse_id(),
                statement=f"SELECT COUNT(*) AS n FROM {table}",
            )
            if result.result and result.result.data_array:
                return int(result.result.data_array[0][0])
        except Exception as e:
            logger.warning(f"Failed to count rows in {table}: {e}")
        return 0

    # ------------------------------------------------------------------
    # Index lifecycle (Databricks-specific)
    # ------------------------------------------------------------------
    def _table_exists(self, collection: str) -> bool:
        """Check if the Delta table backing the index already exists.

        Uses the Unity Catalog REST API which does not require a SQL warehouse,
        so this works on Free Edition without spinning up compute.
        """
        table = self._table_name(collection)
        try:
            self.ws.api_client.do(
                "GET",
                f"/api/2.1/unity-catalog/tables/{table}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            return True
        except Exception as e:
            msg = str(e)
            if "DOES_NOT_EXIST" in msg or "does not exist" in msg.lower() or "404" in msg:
                return False
            # Re-raise unexpected errors
            raise

    def ensure_delta_table(self, collection: str, embedding_dim: int = 1024) -> str:
        """Idempotent: skip if the Delta table already exists, otherwise create it.

        On Databricks Free Edition we cannot create a non-external Delta table
        from outside compute (Unity Catalog security restriction). Callers
        must create the table once via the SQL Editor or UI, then this
        method becomes a no-op for subsequent runs.
        """
        table = self._table_name(collection)
        if self._table_exists(collection):
            logger.info(f"Delta table {table} already exists")
            return table

        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id          STRING,
            text        STRING,
            source      STRING,
            chunk_index INT,
            metadata    STRING,
            embedding   ARRAY<FLOAT>
        ) USING DELTA
        TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
        """
        try:
            self._run_sql(create_sql)
            logger.info(f"Delta table {table} created")
        except Exception as e:
            raise RuntimeError(f"Failed to create Delta table {table}: {e}") from e
        return table

    def create_index_from_table(
        self,
        collection: str,
        embedding_dim: int = 1024,
        primary_key: str = "id",
    ) -> object:
        """Create a Vector Search index on the Delta table with pre-computed embeddings.

        The index uses ``embedding_source_column="embedding"`` so it does NOT call
        Databricks' managed embedder. The pipeline is responsible for providing
        the BGE-M3 vectors.
        """
        table = self.ensure_delta_table(collection, embedding_dim)
        index_name = self._index_name(collection)

        try:
            self.vsc.create_delta_sync_index(
                endpoint_name=self.endpoint,
                index_name=index_name,
                source_table_name=table,
                pipeline_type="TRIGGERED",
                primary_key=primary_key,
                # Use the pre-computed ``embedding`` column; do not call a
                # Databricks-hosted embedding model. The pipeline is
                # responsible for populating the column with BGE-M3 vectors.
                embedding_vector_column="embedding",
                embedding_dimension=embedding_dim,
            )
            logger.info(f"Created Vector Search index {index_name} on {table}")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"Index {index_name} already exists")
            else:
                raise RuntimeError(f"Failed to create index: {e}") from e

        return self.vsc.get_index(endpoint_name=self.endpoint, index_name=index_name)

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------
    def add(
        self,
        collection: str,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Add or update chunks. Writes to the Delta table then syncs the index."""
        if not ids:
            return

        import json as _json

        embedding_dim = len(embeddings[0]) if embeddings else 1024

        # Ensure the underlying Delta table exists, then create the Vector
        # Search index on top of it if it doesn't exist yet. The index
        # creation is idempotent (returns the existing one if already there).
        self.create_index_from_table(
            collection=collection, embedding_dim=embedding_dim,
        )

        table = self._table_name(collection)
        # Idempotent upsert: delete existing ids for this batch, then insert.
        # The Vector Search index is a queryable projection of the table, so
        # DELETE+INSERT is safe and keeps the logic simple.
        if ids:
            id_list = ", ".join(f"'{i}'" for i in ids)
            self._run_sql(f"DELETE FROM {table} WHERE id IN ({id_list})")

        # Insert row-by-row. Spark SQL's parser rejects ``ARRAY[1.0, 2.0]``
        # (square brackets) in INSERT VALUES, even in a single-row statement.
        # The portable form is ``array(1.0, 2.0, ...)`` which infers to
        # ARRAY<FLOAT> when the values are floats. We also keep the
        # single-row-per-INSERT path because the parser has the same bug
        # with multi-row VALUES tuples containing array literals.
        for _id, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
            chunk_index = int(meta.get("chunk_index", 0)) if isinstance(meta, dict) else 0
            source = str(meta.get("source", "")) if isinstance(meta, dict) else ""
            meta_json = _json.dumps(meta, ensure_ascii=False) if isinstance(meta, dict) else "{}"
            emb_str = ", ".join(f"{float(x):.7f}" for x in emb)
            doc_escaped = doc.replace("'", "''")
            meta_escaped = meta_json.replace("'", "''")
            insert_sql = f"""
            INSERT INTO {table} (id, text, source, chunk_index, metadata, embedding)
            VALUES ('{_id}', '{doc_escaped}', '{source}', {chunk_index}, '{meta_escaped}', array({emb_str}))
            """
            self._run_sql(insert_sql)
        # (square brackets) in INSERT VALUES, even in a single-row statement.
        # The portable form is ``array(1.0, 2.0, ...)`` which infers to
        # ARRAY<FLOAT> when the values are floats. We also keep the
        # single-row-per-INSERT path because the parser has the same bug
        # with multi-row VALUES tuples containing array literals.
        for _id, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
            chunk_index = int(meta.get("chunk_index", 0)) if isinstance(meta, dict) else 0
            source = str(meta.get("source", "")) if isinstance(meta, dict) else ""
            meta_json = _json.dumps(meta, ensure_ascii=False) if isinstance(meta, dict) else "{}"
            emb_str = ", ".join(f"{float(x):.7f}" for x in emb)
            doc_escaped = doc.replace("'", "''")
            meta_escaped = meta_json.replace("'", "''")
            insert_sql = f"""
            INSERT INTO {table} (id, text, source, chunk_index, metadata, embedding)
            VALUES ('{_id}', '{doc_escaped}', '{source}', {chunk_index}, '{meta_escaped}', array({emb_str}))
            """
            self._run_sql(insert_sql)

        # Trigger index sync
        self._sync_index(collection)

    def _sync_index(self, collection: str) -> None:
        """Trigger TRIGGERED sync on the Vector Search index.

        TRIGGERED sync is async on the server; this method fires the request
        and returns. Callers that need to wait for the index to become
        queryable should poll ``describe()`` themselves — see
        ``scripts/smoke_test_databricks._wait_for_index_ready``.
        """
        index_name = self._index_name(collection)
        try:
            index = self.vsc.get_index(endpoint_name=self.endpoint, index_name=index_name)
            index.sync()
            logger.info(f"Index {index_name} sync triggered")
        except Exception as e:
            # Common during first-time provisioning ("Vector index is not
            # ready"). The caller will poll for readiness and the next
            # ingest will retry the sync.
            logger.debug(f"Index sync warning: {e}")

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------
    def query(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 20,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """Top-k ANN search against the Vector Search index."""
        index_name = self._index_name(collection)
        try:
            index = self.vsc.get_index(endpoint_name=self.endpoint, index_name=index_name)
        except Exception as e:
            logger.warning(f"Index {index_name} not available: {e}")
            return []

        filters_json = None
        if where:
            import json as _json
            filters_json = _json.dumps(where)

        try:
            result = index.similarity_search(
                query_vector=query_embedding,
                columns=["id", "text", "source", "chunk_index", "metadata"],
                num_results=top_k,
                filters=filters_json,
            )
        except Exception as e:
            logger.warning(f"Vector Search query failed: {e}")
            return []

        out: list[dict] = []
        import json as _json
        data_array = result.get("result", {}).get("data_array", [])
        for row in data_array:
            # row: [id, text, source, chunk_index, metadata, score]
            _id, text, source, chunk_index, metadata, score = row[:6]
            try:
                meta_dict = _json.loads(metadata) if isinstance(metadata, str) else (metadata or {})
            except Exception:
                meta_dict = {}
            meta_dict.setdefault("source", source)
            meta_dict.setdefault("chunk_index", chunk_index)
            out.append(
                {
                    "id": _id,
                    "text": text or "",
                    "metadata": meta_dict,
                    "score": float(score) if score is not None else 0.0,
                    "source_retriever": "vector",
                }
            )
        return out

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _sql_array(self, items) -> str:
        """Format a Python list as a SQL ARRAY literal."""
        if not items:
            return "()"
        if isinstance(items[0], (int, float)):
            return "(" + ", ".join(str(x) for x in items) + ")"
        if isinstance(items[0], list):
            inner = ", ".join(
                "ARRAY[" + ", ".join(f"{float(x):.7f}" for x in row) + "]" for row in items
            )
            return f"ARRAY({inner})"
        # strings — escape single quotes
        return "(" + ", ".join("'" + str(x).replace("'", "''") + "'" for x in items) + ")"

    def _warehouse_id(self) -> Optional[str]:
        """Pick the first available SQL warehouse (Free Edition ships one)."""
        try:
            # ``warehouses.list()`` returns a generator; materialize first so
            # we can fall back to the first entry if none are running.
            warehouses = list(self.ws.warehouses.list())
            for w in warehouses:
                state = getattr(w, "state", None)
                if state and str(state).lower() in ("running", "started", "idle"):
                    return w.id
            if warehouses:
                return warehouses[0].id
        except Exception as e:
            logger.warning(f"Could not list warehouses: {e}")
        return None

    def _run_sql(self, sql: str) -> None:
        wh = self._warehouse_id()
        if not wh:
            raise RuntimeError("No SQL warehouse available on this workspace")
        result = self.ws.statement_execution.execute_statement(
            warehouse_id=wh,
            statement=sql,
            wait_timeout="30s",
        )
        status = getattr(result.status, "state", None) if result.status else None
        if status and "FAIL" in str(status).upper():
            # Dump the full result to help diagnose; the SDK normally returns
            # a status.error but newer versions nest the detail in result.error
            raise RuntimeError(
                f"SQL failed (state={status}): "
                f"status={getattr(result, 'status', None)!r}, "
                f"error={getattr(result, 'error', None)!r}, "
                f"manifest={getattr(result, 'manifest', None)!r}, "
                f"result={getattr(result, 'result', None)!r}"
            )
