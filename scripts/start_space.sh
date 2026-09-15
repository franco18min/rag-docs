#!/usr/bin/env bash
# Hugging Face Spaces entrypoint: API :8000 + ingest sample + Streamlit :7860
# Single process tree (API in background, Streamlit in foreground). Do not run ingest CLI.
set -eu

export ENABLE_RERANK="${ENABLE_RERANK:-false}"
export GEMINI_MODEL="${GEMINI_MODEL:-gemini-flash-lite-latest}"
export VECTOR_STORE_BACKEND="${VECTOR_STORE_BACKEND:-chroma}"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
API_URL="http://${API_HOST}:${API_PORT}"

uvicorn app.main:app --host 0.0.0.0 --port "${API_PORT}" &
API_PID=$!

python - <<'PY'
import json
import sys
import time
import urllib.error
import urllib.request

base = "http://127.0.0.1:8000"
deadline = time.time() + 180
while time.time() < deadline:
    try:
        with urllib.request.urlopen(base + "/health", timeout=5) as resp:
            if resp.status == 200:
                break
    except (urllib.error.URLError, TimeoutError, OSError):
        time.sleep(2)
else:
    print("API did not become healthy in time", file=sys.stderr)
    sys.exit(1)

payload = json.dumps(
    {
        "source_dir": "./data/sample",
        "collection": "spark_docs",
        "rebuild": True,
    }
).encode()
req = urllib.request.Request(
    base + "/ingest",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=600) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        print("ingest:", body[:500])
except urllib.error.HTTPError as e:
    print("ingest failed:", e.read().decode("utf-8", errors="replace"), file=sys.stderr)
    sys.exit(1)
PY

export RAG_API_URL="${API_URL}"
exec streamlit run app/streamlit_app.py \
    --server.port 7860 \
    --server.address 0.0.0.0 \
    --server.headless true
