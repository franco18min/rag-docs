# Deploy en Databricks (Free Edition)

> Estado: guía para Databricks Free Edition. Reemplazá el host por el de
> **tu** workspace (`https://<workspace-id>.cloud.databricks.com`). No uses
> un workspace personal de terceros.

Este documento describe cómo deployar el RAG pipeline en una workspace
de Databricks Free Edition, dejando recursos prendidos solo el tiempo
necesario para la validación.

## Resumen

```bash
# 1. Instalar dependencias
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configurar credenciales (ver sección "PAT" abajo)
cp .env.example .env
# Editar .env: pegar tu DATABRICKS_TOKEN y DATABRICKS_HOST

# 3. Provisionar catalog, schema, endpoint (UI o API)
#    (Ver "Configuración manual" más abajo)

# 4. Smoke test end-to-end (crea tabla + index, ingiere 5 chunks, query, cleanup)
export DATABRICKS_HOST='https://<workspace-id>.cloud.databricks.com'
export DATABRICKS_TOKEN='dapi...'
python scripts/smoke_test_databricks.py
```

## Arquitectura

```
┌────────────────────────────────────────┐
│  RAG Pipeline (local Python)           │
│  - BGE-M3 embeddings (local GPU/CPU)   │
│  - BGE-reranker cross-encoder          │
│  - Gemini generation (API)             │
└────────────┬───────────────────────────┘
             │ similarity_search
             ▼
┌────────────────────────────────────────┐
│  Databricks Free Edition               │
│  - Delta table (chunks + embeddings)   │
│  - Vector Search / AI Search endpoint  │
│  - SQL warehouse (serverless starter)  │
└────────────────────────────────────────┘
```

- **Fuente de verdad**: la Delta table `rag_docs.production.<collection>`
  contiene los chunks, metadatos y embeddings pre-computados por BGE-M3.
- **Índice de Vector Search**: índice `rag_docs.production.<collection>_idx`
  (sufijo `_idx` para evitar conflicto de nombre con la tabla) sobre
  la columna `embedding` (`ARRAY<FLOAT>`).
- **Lado local**: el pipeline corre en una máquina con Python y
  acceso al workspace vía REST. No requiere cluster dedicado.

## Configuración manual (Free Edition)

### 1. Crear Personal Access Token (PAT)

1. Databricks workspace → Click en tu avatar (arriba a la derecha) → **User Settings**.
2. **Developer** → **Access tokens** → **Generate new token**.
3. Nombre: `rag-docs-dev-<fecha>` (recomendable rotar cada 30 días).
4. Lifetime: el mínimo necesario (Free Edition default es 90 días).
5. Scope: déjalo en "all-apis" para simplificar.
6. **⚠️ Copialo inmediatamente** — no se vuelve a mostrar.

```bash
# Probar el token
curl -H "Authorization: Bearer dapi..." \
     https://dbc-xxxxx.cloud.databricks.com/api/2.0/preview/scim/v2/Me
```

### 2. Crear Catalog (vía UI)

La API REST de Unity Catalog no permite crear catalogs con Default Storage
en Free Edition. Hay que hacerlo por UI:

1. Catalog page (sidebar izquierdo) → **Create Catalog**.
2. Catalog name: `rag_docs`.
3. Catalog type: **Standard**.
4. Storage location: **Use default storage** (recomendado).
5. **Create**.

### 3. Crear Schema (vía API o UI)

```bash
# Por API (más rápido)
$env:DATABRICKS_HOST='https://...'
$env:DATABRICKS_TOKEN='dapi...'
.\.venv\Scripts\python.exe -c "
from databricks.sdk import WorkspaceClient
ws = WorkspaceClient()
ws.schemas.create(
    catalog_name='rag_docs',
    name='production',
    comment='RAG Docs production schema',
)
"
```

O desde la UI: catalog `rag_docs` → **Create schema** → `production`.

### 4. Crear Vector Search endpoint (vía API o UI)

```python
from databricks.ai_search.client import AISearchClient
client = AISearchClient()
client.create_endpoint_and_wait(
    name="rag_docs_endpoint",
    endpoint_type="STANDARD",
    # budget_policy_id="...",  # opcional
)
```

O desde la UI: Compute → **Vector Search** → **Create endpoint** →
nombre `rag_docs_endpoint` → tipo `STANDARD` → Create.

> ⏱️ Tarda ~30 segundos en estar ONLINE.

### 5. Crear Delta table (vía SQL Editor)

**La Free Edition NO permite crear Delta tables no-externas vía API** (error
`UNITY_CATALOG_EXTERNAL_CREATE_TABLE_REQUEST_FOR_NON_EXTERNAL_TABLE_DENIED`).
Hay que hacerlo desde el SQL Editor:

1. Sidebar → **SQL Editor** → New query.
2. Catalog dropdown (top): `rag_docs`.
3. Schema dropdown (top): `production`.
4. Query:

```sql
CREATE TABLE IF NOT EXISTS rag_docs.production.spark_docs (
    id          STRING,
    text        STRING,
    source      STRING,
    chunk_index INT,
    metadata    STRING,
    embedding   ARRAY<FLOAT>
) USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
```

5. **Run all** (botón verde, dropdown "1000" — tarda ~5s).

> El `delta.enableChangeDataFeed` es necesario para que Vector Search
> pueda hacer sync con TRIGGERED pipeline.

### 6. Configurar `.env`

```env
DATABRICKS_HOST=https://<workspace-id>.cloud.databricks.com
DATABRICKS_TOKEN=dapi...  # ⚠️ no commitear (está en .gitignore)
DATABRICKS_CATALOG=rag_docs
DATABRICKS_SCHEMA=production
DATABRICKS_VECTOR_ENDPOINT=rag_docs_endpoint
VECTOR_STORE_BACKEND=databricks  # alterna entre chroma (dev) y databricks (prod)
```

## Uso desde el pipeline

Una vez configurado, el pipeline usa el backend Databricks automáticamente:

```python
from app.core.pipeline import RAGPipeline

pipeline = RAGPipeline()  # usa settings.vector_store_backend
pipeline.ingest(
    documents=load_documents("./data/raw"),
    collection="spark_docs",
    rebuild=True,
)

result = pipeline.query("¿Qué es Delta Lake?")
print(result["answer"])
print(result["citations"])
```

## Problemas que aprendimos en producción

### 1. Nombres del SDK: `AISearchClient`, no `VectorSearchClient`

`databricks-vectorsearch==0.75` es un **re-export liviano** de
`databricks-ai-search==0.78`. Ambos `from databricks.vector_search.client
import VectorSearchClient` y `from databricks.ai_search.client import
AISearchClient` resuelven a la misma clase, pero el backend rechaza
create_index con el error "Vector index must be created via AI Search APIs"
si usás el path equivocado.

**Solución**: usar directamente `AISearchClient`.

```python
# requirements.txt
databricks-vectorsearch<0.75  # solo para back-compat
databricks-ai-search>=0.78    # lo que realmente se importa
databricks-sdk
```

### 2. Nombres únicos en Unity Catalog

El Vector Search index **no puede llamarse igual que la Delta table**
en el mismo schema. Si tu tabla es `spark_docs`, el index debe ser
`spark_docs_idx` (sufijo u otro nombre distinto).

```python
def _index_name(self, collection: str) -> str:
    return f"{self.catalog}.{self.schema}.{collection}_idx"
```

Error típico:

```
UC entity rag_docs.production.spark_docs already exists. Please use a
unique name in UC for the index name.
```

### 3. ARRAY literals en INSERT

Spark SQL **rechaza** `ARRAY[1.0, 2.0]` (con corchetes) en INSERT VALUES:

```
[PARSE_SYNTAX_ERROR] Syntax error at or near ',': missing ']'
```

**Solución**: usar `array(1.0, 2.0, ...)` (función, inferencia de tipo)
o `CAST(ARRAY(1.0, 2.0) AS ARRAY<FLOAT>)` (explícito).

También rechaza multi-row `VALUES (...), (...)` cuando los tuples
contienen array literals — un INSERT por fila es el camino seguro.

### 4. Generators en `warehouses.list()`

`ws.warehouses.list()` retorna un **generator** que se agota al iterar.
No subscriptable.

```python
# ❌ Mal
for w in ws.warehouses.list():
    if w.state == "RUNNING": return w.id
return ws.warehouses.list()[0].id  # ¡TypeError!

# ✅ Bien
warehouses = list(ws.warehouses.list())
for w in warehouses:
    if w.state == "RUNNING": return w.id
if warehouses:
    return warehouses[0].id
```

### 5. Orden de carga: `.env` antes del cliente

El cliente legacy (`VectorSearchClient.__init__` en `databricks-vectorsearch<0.75`)
llama a `mlflow.utils.databricks_utils.get_databricks_host_creds()` que
lee `DATABRICKS_HOST` / `DATABRICKS_TOKEN` del environment directamente,
**ignorando Pydantic settings**. Si importás el cliente antes de cargar
`.env`, falla con "Reading Databricks credential configuration failed".

```python
# ❌ Mal
from databricks.ai_search.client import AISearchClient  # lee env vars ya
from dotenv import load_dotenv
load_dotenv()  # tarde

# ✅ Bien
from dotenv import load_dotenv
load_dotenv(".env")
from databricks.ai_search.client import AISearchClient  # ya tiene las vars
```

### 6. Provisioning del index toma 2-5 minutos

La primera vez que creás un index sobre un endpoint STANDARD, el ciclo
de vida es:

```
PROVISIONING_ENDPOINT → PROVISIONING_INDEX → PROVISIONING_PIPELINE_RESOURCES
→ PROVISIONING_INITIAL_SNAPSHOT → ONLINE_TRIGGERED_UPDATE
```

`index.sync()` retorna "Vector index is not ready" hasta que `ready=True`.
**No hacer tight retry** — solo poll `index.describe()['status']['ready']`
cada 15s con timeout de 10 min. Ver `scripts/smoke_test_databricks.py`
para el patrón completo.

### 7. Carga `.env` antes que el cliente, en scripts standalone

El script smoke test debe `load_dotenv()` antes de importar
`DatabricksVectorStore` o cualquier cosa que cree el cliente:

```python
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.core.vector_store_databricks import DatabricksVectorStore
```

## Costo y límites Free Edition

| Recurso | Free Edition | Costo Standard |
|---------|-------------|----------------|
| Vector Search endpoint | 1 endpoint, STANDARD | $0.50/hr endpoint + storage |
| Delta table size | Sin límite explícito (storage default incluido) | $0.025/GB-mes |
| SQL warehouse | Serverless starter incluido | $0.07/DBU |
| Catalog | Default storage incluido | $0.025/GB-mes |
| PAT lifetime | Hasta 90 días | Configurable |

**Para validar el MVP**: dejar el endpoint prendido ~30 min mientras corrés
ingest + `evaluate_light.py` + smoke test. Después, cleanup. RAGAS full
no está soportado.

## Limpieza (importante — no dejar prendido)

```python
# 1. Borrar el index
from databricks.ai_search.client import AISearchClient
client = AISearchClient()
client.delete_index(
    endpoint_name="rag_docs_endpoint",
    index_name="rag_docs.production.spark_docs_idx",
)

# 2. Borrar la tabla
from databricks.sdk import WorkspaceClient
ws = WorkspaceClient()
ws.api_client.do(
    "DELETE",
    "/api/2.1/unity-catalog/tables/rag_docs.production.spark_docs",
    headers={"Authorization": f"Bearer {ws.config.token}"},
)

# 3. Borrar el endpoint (libera $$$)
client.delete_endpoint("rag_docs_endpoint")

# 4. Opcional: borrar schema y catalog
ws.schemas.delete("rag_docs", "production")
ws.catalogs.delete("rag_docs")
```

## Pruebas

| Test | Comando | Tiempo | Qué valida |
|------|---------|--------|------------|
| Smoke test (4-dim) | `python scripts/smoke_test_databricks.py` | 3-5 min | Ida y vuelta end-to-end con embeddings dummy |
| Ingest real | `python -m scripts.ingest --source data/raw --collection spark_docs --rebuild` | 5-10 min | BGE-M3 embed + Delta write + Vector Search sync |
| Eval light | `python scripts/evaluate_light.py` | 5-10 min | LLM-as-judge (RAGAS full no soportado) |
| FastAPI local | `python -m uvicorn app.main:app` | inmediato | Endpoint /query end-to-end |

## Resolución de problemas

### "UC entity ... already exists"

Conflicto de nombres entre tabla e index. Cambiá el sufijo del index
(`_idx`) o usá un collection name distinto.

### "Vector index must be created via AI Search APIs"

Estás usando el SDK viejo o importás `VectorSearchClient` yendo al
backend equivocado. Forzá `from databricks.ai_search.client import
AISearchClient` directamente.

### "PARSE_SYNTAX_ERROR ... missing ']'"

Estás usando `ARRAY[1.0, 2.0]` con corchetes en INSERT. Usá
`array(1.0, 2.0)` o `CAST(ARRAY(1.0, 2.0) AS ARRAY<FLOAT>)`.

### El index se queda en PROVISIONING_ENDPOINT 5+ minutos

Espera. Si después de 10 min sigue ahí, borra el index y creálo de
nuevo. A veces el primer sync se atasca.

### Rotación del PAT

Si el PAT se filtró en logs (chat, screenshots, etc.), regenerá
inmediatamente en User Settings → Developer → Access tokens → Manage →
**Revoke** + generar nuevo. Actualizar `.env`.

## Referencias

- [Databricks Vector Search docs](https://docs.databricks.com/en/generative-ai/vector-search.html)
- [Delta Lake Time Travel](https://docs.delta.io/latest/delta-batch.html#query-an-older-snapshot-of-a-table-time-travel)
- [BGE-M3 paper](https://arxiv.org/abs/2402.03216)
- [RRF (Reciprocal Rank Fusion)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
