"""Create the smoke_test Delta table via Unity Catalog API (no SQL warehouse needed)."""

import json
import os
import sys
from pathlib import Path
from urllib import request
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

host = os.environ.get("DATABRICKS_HOST", "https://<workspace-id>.cloud.databricks.com")
token = Path(".env").read_text(encoding="utf-8") if Path(".env").exists() else ""
# Fall back to scraping from .env
from app.config import settings

token = settings.databricks_token

# The default storage location from the catalog. The table needs a sub-path.
storage_root = "s3://<catalog-storage-root>"

body = {
    "catalog_name": "rag_docs",
    "schema_name": "production",
    "name": "smoke_test",
    "table_type": "MANAGED",
    "data_source_format": "DELTA",
    "storage_location": f"{storage_root}/tables/smoke_test",
    "columns": [
        {
            "name": "id",
            "type_name": "STRING",
            "type_text": "STRING",
            "type_json": json.dumps({"name": "id", "type": "string", "nullable": True}),
            "position": 0,
        },
        {
            "name": "text",
            "type_name": "STRING",
            "type_text": "STRING",
            "type_json": json.dumps({"name": "text", "type": "string", "nullable": True}),
            "position": 1,
        },
        {
            "name": "source",
            "type_name": "STRING",
            "type_text": "STRING",
            "type_json": json.dumps({"name": "source", "type": "string", "nullable": True}),
            "position": 2,
        },
        {
            "name": "chunk_index",
            "type_name": "INT",
            "type_text": "INT",
            "type_json": json.dumps({"name": "chunk_index", "type": "integer", "nullable": True}),
            "position": 3,
        },
        {
            "name": "metadata",
            "type_name": "STRING",
            "type_text": "STRING",
            "type_json": json.dumps({"name": "metadata", "type": "string", "nullable": True}),
            "position": 4,
        },
        {
            "name": "embedding",
            "type_name": "ARRAY",
            "type_text": "ARRAY<FLOAT>",
            "type_json": json.dumps(
                {
                    "name": "embedding",
                    "type": {"type": "array", "elementType": "float"},
                    "nullable": True,
                }
            ),
            "position": 5,
        },
    ],
}

req = request.Request(
    f"{host}/api/2.1/unity-catalog/tables",
    data=json.dumps(body).encode("utf-8"),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="POST",
)

try:
    with request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print(f"OK: full_name={result.get('full_name')} table_id={result.get('table_id')}")
except HTTPError as e:
    body_text = e.read().decode("utf-8", errors="replace")
    print(f"ERROR {e.code}: {body_text}")
    sys.exit(1)
