"""Tear down the Databricks Vector Search / Delta deployment.

Removes, in order:
    1. The Vector Search index (rag_docs.production.<collection>_idx)
    2. The Delta table (rag_docs.production.<collection>)
    3. The Vector Search endpoint (rag_docs_endpoint)
    4. The schema (rag_docs.production) — if empty
    5. The catalog (rag_docs) — if empty

Use --keep-endpoint or --keep-catalog to skip those steps.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from databricks.ai_search.client import AISearchClient
from databricks.sdk import WorkspaceClient


def delete_index(client, endpoint, name):
    try:
        client.delete_index(endpoint_name=endpoint, index_name=name)
        print(f"  OK  deleted index {name}")
        return True
    except Exception as e:
        print(f"  ERR delete index: {e}")
        return False


def delete_table(ws, table_full):
    try:
        ws.api_client.do(
            "DELETE",
            f"/api/2.1/unity-catalog/tables/{table_full}",
            headers={"Authorization": f"Bearer {ws.config.token}"},
        )
        print(f"  OK  deleted table {table_full}")
        return True
    except Exception as e:
        print(f"  ERR delete table: {e}")
        return False


def delete_endpoint(client, name):
    try:
        client.delete_endpoint(name)
        print(f"  OK  deleted endpoint {name}")
        return True
    except Exception as e:
        print(f"  ERR delete endpoint: {e}")
        return False


def delete_schema(ws, catalog, schema):
    try:
        ws.schemas.delete(catalog, schema)
        print(f"  OK  deleted schema {catalog}.{schema}")
        return True
    except Exception as e:
        print(f"  ERR delete schema: {e}")
        return False


def delete_catalog(ws, catalog):
    try:
        ws.catalogs.delete(catalog)
        print(f"  OK  deleted catalog {catalog}")
        return True
    except Exception as e:
        print(f"  ERR delete catalog: {e}")
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", default=os.environ.get("DATABRICKS_CATALOG", "rag_docs"))
    p.add_argument("--schema", default=os.environ.get("DATABRICKS_SCHEMA", "production"))
    p.add_argument("--endpoint", default=os.environ.get("DATABRICKS_VECTOR_ENDPOINT", "rag_docs_endpoint"))
    p.add_argument("--collection", default=os.environ.get("COLLECTION_NAME", "spark_docs"))
    p.add_argument("--keep-endpoint", action="store_true")
    p.add_argument("--keep-catalog", action="store_true")
    args = p.parse_args()

    print("Cleanup target:")
    print(f"  catalog={args.catalog}  schema={args.schema}")
    print(f"  endpoint={args.endpoint}  collection={args.collection}\n")

    table_full = f"{args.catalog}.{args.schema}.{args.collection}"
    index_full = f"{args.catalog}.{args.schema}.{args.collection}_idx"

    ws = WorkspaceClient()
    client = AISearchClient()

    print("[1/5] Deleting index ...")
    delete_index(client, args.endpoint, index_full)

    print("\n[2/5] Deleting table ...")
    delete_table(ws, table_full)

    if not args.keep_endpoint:
        print("\n[3/5] Deleting endpoint ...")
        delete_endpoint(client, args.endpoint)
    else:
        print("\n[3/5] Skipping endpoint (--keep-endpoint)")

    if not args.keep_catalog:
        print("\n[4/5] Deleting schema ...")
        delete_schema(ws, args.catalog, args.schema)

        print("\n[5/5] Deleting catalog ...")
        delete_catalog(ws, args.catalog)
    else:
        print("\n[4/5] Skipping schema (--keep-catalog)")
        print("[5/5] Skipping catalog (--keep-catalog)")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
