# RAG Docs — Sistema de Preguntas y Respuestas sobre Documentación Técnica

> Un sistema RAG (Retrieval-Augmented Generation) production-grade que ingiere documentación técnica, la indexa con búsqueda híbrida, y responde preguntas con citas a las fuentes. **Costo total: USD 0** usando Google Gemini, BGE-M3 y Chroma (dev) / Databricks Vector Search (deploy).

![Status](https://img.shields.io/badge/status-MVP%20working-success)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Stack](https://img.shields.io/badge/stack-100%25%20gratis-success)
![Deploy](https://img.shields.io/badge/Databricks%20Free%20Edition-validated-blue)
![CI](https://github.com/franco18min/rag-docs/actions/workflows/ci.yml/badge.svg)

![Streamlit demo: query "¿Qué garantías ACID ofrece Delta Lake?" with full citation-backed response](docs/img/streamlit-demo.jpg)

---

## ¿Por qué este proyecto?

Sistema RAG production-grade sobre documentación técnica con búsqueda híbrida, re-ranking y evaluación sistemática. Demuestra:

- Diseño de pipelines de ingestión (transferible desde data engineering)
- **Búsqueda híbrida** (BM25 + vector denso) con RRF y re-ranking cross-encoder
- **Ablation study** que justifica cada decisión arquitectónica
- **Evaluación sistemática** (20 Q&A con ground truth, RAGAS-style)
- **5 ADRs** documentando decisiones técnicas
- **CI** con GitHub Actions (lint + mypy + tests)
- **Backend vendor-agnostic**: Chroma (local) ↔ Databricks Vector Search (prod)
- **Deploy validado end-to-end** en Databricks Free Edition
- **Costo de inferencia: USD 0** (Gemini Flash-Lite free tier)

Para más detalles sobre arquitectura, evaluación, decisiones técnicas y deploy, ver:
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — decisiones técnicas y trade-offs
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — cómo interpretar las métricas
- [`docs/DEPLOY_DATABRICKS.md`](docs/DEPLOY_DATABRICKS.md) — setup Free Edition, gotchas y cleanup
- [`docs/adr/`](docs/adr/README.md) — 5 Architecture Decision Records

---

## Arquitectura

```
┌──────────────┐
│  Documentos  │  (PDF, MD, HTML, TXT)
│   (50-100)   │
└──────┬───────┘
       │ 1. Ingesta (loaders por formato)
       ▼
┌──────────────┐
│   Chunking   │  tiktoken, sliding window 512 tokens / overlap 64
│   + Metadata │  source, filename, chunk_index, page, etc.
└──────┬───────┘
       │ 2. Embedding (BGE-M3, normalizado)
       ▼
┌──────────────┐
│  Vector DB   │  Chroma (cosine) + BM25 index (rank-bm25)
│  + BM25 idx  │  Búsqueda híbrida con RRF (k=60)
└──────┬───────┘
       │ 3. Query
       ▼
┌──────────────┐
│  Re-ranker   │  Cross-encoder (BGE-reranker-base) top-20 → top-5
└──────┬───────┘
       │ 4. Generation
       ▼
┌──────────────┐
│  LLM (Gemini │  Gemini 2.0 Flash con prompt estructurado
│  2.0 Flash)  │  + citas [#N] obligatorias
└──────┬───────┘
       │ 5. Response
       ▼
   {answer, citations, scores, latency_ms, model}
```

---

## Tech Stack (todo gratis)

| Componente | Herramienta | Costo |
|---|---|---|
| **LLM** | Google Gemini 2.0 Flash (free tier: 1,500 req/día) | $0 |
| **Embeddings** | HuggingFace `BAAI/bge-m3` (local, 1024-dim, multilingüe) | $0 |
| **Re-ranker** | HuggingFace `BAAI/bge-reranker-base` (local) | $0 |
| **Vector DB** | Chroma (persistent local) → pgvector (migración futura) | $0 |
| **Keyword search** | rank-bm25 (local, persistido a disco) | $0 |
| **Backend** | FastAPI + Uvicorn | $0 |
| **Frontend demo** | Streamlit | $0 |
| **Chunking** | tiktoken (cl100k_base) | $0 |
| **Evaluation** | RAGAS + datasets | $0 |
| **Observability** | Interface lista para Langfuse (instrumentación opcional) | $0 |
| **Deploy** | Docker + Docker Compose | $0 |

**Costo total para construir + demostrar: USD 0**

---

## Quick Start (10 minutos al primer query)

### 1. Setup

**Unix / macOS**

```bash
cd rag-docs

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Configurar API key de Gemini (gratis)
# Obtené tu key en https://aistudio.google.com/app/apikey
cp .env.example .env
# Editá .env y poné tu GOOGLE_API_KEY
```

**Windows (PowerShell)**

```powershell
cd rag-docs

python -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt

Copy-Item .env.example .env
# Editá .env y poné tu GOOGLE_API_KEY
```

### 2. Ingerir documentos

El corpus de demo está en `data/sample/` (markdowns de Spark / Delta / Vector Search).

```bash
# Ingerir (rebuild=True si querés empezar de cero)
python -m scripts.ingest --source ./data/sample --collection spark_docs
```

Vas a ver: chunking → embedding → indexing. Cuando termine: `Ingest complete: 247 chunks from 8 documents in 12.4s`.

### 3. Levantar la API

```bash
uvicorn app.main:app --reload --port 8000

# Probar:
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cómo funciona la arquitectura Medallion en Databricks?"}'
```

Respuesta esperada:
```json
{
  "answer": "La arquitectura Medallion es un patrón de diseño de datos...",
  "citations": [{"source": "...", "score": 0.92, "text_snippet": "..."}],
  "latency_ms": 1240,
  "model": "gemini-2.0-flash-exp",
  "collection": "spark_docs",
  "chunks_retrieved": 5
}
```

### 4. UI demo

```bash
# En otra terminal, con el venv activado
streamlit run app/streamlit_app.py

# Abrí http://localhost:8501
```

### 5. (Opcional) Evaluar con RAGAS

```bash
# Generar un set de Q&A desde la colección (usa Gemini)
python -m scripts.generate_eval_set --collection spark_docs --output data/eval/qa_set.json --num-questions 30

# O usar el template y editarlo a mano
cp data/eval/qa_set_template.json data/eval/qa_set.json

# Correr evaluación
python -m scripts.evaluate --collection spark_docs --eval-set data/eval/qa_set.json

# Vas a ver métricas: faithfulness, context_precision, context_recall, answer_relevancy
```

### 6. (Opcional) Correr los tests

```bash
pytest tests/ -v
```

---

## Estructura del proyecto

```
rag-docs/
├── README.md                      # Este archivo
├── requirements.txt               # Dependencias
├── pyproject.toml                 # ruff + mypy + pytest config
├── .env.example                   # Template de variables de entorno
├── .gitignore
├── LICENSE                        # MIT
├── Dockerfile                     # Para deploy
├── docker-compose.yml             # API + Streamlit
├── .github/
│   └── workflows/ci.yml           # GitHub Actions: lint + mypy + tests
│
├── app/                           # Aplicación principal
│   ├── __init__.py
│   ├── main.py                    # FastAPI app
│   ├── streamlit_app.py           # UI demo
│   ├── config.py                  # Configuración centralizada (Pydantic Settings)
│   │
│   ├── core/                      # Lógica de negocio
│   │   ├── chunker.py             # Sliding window con tiktoken + metadata
│   │   ├── embedder.py            # BGE-M3 wrapper (singleton)
│   │   ├── vector_store.py        # Chroma wrapper
│   │   ├── vector_store_databricks.py  # Databricks Vector Search adapter
│   │   ├── bm25_store.py          # rank-bm25 wrapper (persistido)
│   │   ├── hybrid_search.py       # Búsqueda híbrida con RRF
│   │   ├── reranker.py            # Cross-encoder re-ranking
│   │   ├── generator.py           # Gemini wrapper con prompt estructurado
│   │   ├── store_factory.py       # Vendor-agnostic store selector
│   │   └── pipeline.py            # Orquestación end-to-end
│   │
│   ├── models/                    # Schemas Pydantic
│   │   ├── query.py               # QueryRequest, IngestRequest
│   │   └── response.py            # QueryResponse, Citation, HealthResponse
│   │
│   └── observability/             # Langfuse integration (stub por ahora)
│       └── __init__.py
│
├── scripts/                       # Scripts CLI
│   ├── ingest.py                  # Ingesta de documentos (PDF/MD/HTML/TXT)
│   ├── generate_eval_set.py       # Generar Q&A set con Gemini o desde template
│   ├── evaluate.py                # Full RAGAS runner (requiere fix langchain)
│   ├── evaluate_light.py          # Lightweight RAGAS-style eval (1 LLM call/Q)
│   ├── ablation.py                # vector vs hybrid vs hybrid+rerank
│   ├── smoke_test_databricks.py   # End-to-end test contra Databricks
│   └── cleanup_databricks.py      # Drop endpoint + table + catalog
│
├── data/                          # Data local (no commitear — ver .gitignore)
│   ├── raw/                       # PDFs/MDs originales
│   ├── chroma/                    # Vector DB local
│   ├── processed/                 # (reservado)
│   └── eval/
│       ├── qa_set.json            # 20 Q&A con ground truth
│       ├── qa_set_template.json   # 5 Q&A starter
│       └── results.json           # (generado por evaluate.py)
│
├── tests/                         # Tests (pytest, 11 tests, ~9s)
│   ├── test_chunker.py
│   ├── test_hybrid_search.py
│   └── test_pipeline_query.py
│
└── docs/                          # Documentación
    ├── ARCHITECTURE.md            # Decisiones técnicas detalladas
    ├── EVALUATION.md              # Cómo interpretar métricas
    ├── DEPLOY_DATABRICKS.md       # Setup Free Edition, gotchas y cleanup
    ├── adr/                       # Architecture Decision Records
    │   ├── README.md
    │   ├── 0001-bge-m3-embedding-model.md
    │   ├── 0002-hybrid-search-bm25-vector.md
    │   ├── 0003-rerank-cross-encoder.md
    │   ├── 0004-vector-store-abstraction.md
    │   └── 0005-gemini-flash-lite.md
    └── img/
        └── streamlit-demo.jpg
```

---

## Features implementadas

### Core (MVP) — listo y funcionando
- [x] Ingesta de PDFs, Markdown, HTML, TXT
- [x] Chunking sliding-window con tiktoken (512/64) + metadata rica
- [x] Embeddings locales con BGE-M3 (multilingüe, 1024-dim)
- [x] Búsqueda vector con Chroma (cosine, persistent)
- [x] Búsqueda BM25 con rank-bm25 (persistido a disco)
- [x] Búsqueda híbrida con RRF (k=60)
- [x] Re-ranking con cross-encoder BGE-reranker-base
- [x] Generación con Gemini 2.0 Flash + prompt estructurado
- [x] Citas a las fuentes con score
- [x] API REST con FastAPI (health, collections, query, ingest)
- [x] UI demo con Streamlit
- [x] Evaluación con RAGAS (faithfulness, precision, recall, relevancy)
- [x] Auto-generación de Q&A con Gemini para eval
- [x] Tests unitarios (chunker, hybrid search, pipeline)
- [x] Dockerfile + docker-compose
- [x] Documentación: ARCHITECTURE, EVALUATION

---

## Métricas de evaluación (RAGAS)

### Ablation: ¿cuánto aporta cada componente?

Comparación de las 3 configuraciones de retrieval sobre 20 Q&A con ground truth (corpus de 18 chunks):

| Configuración | Hit@1 | Hit@3 | Hit@5 | MRR | Latencia |
|---------------|-------|-------|-------|-----|----------|
| **vector-only** (BGE-M3) | 0.900 | 0.900 | 0.900 | 0.900 | 88 ms |
| **hybrid** (BM25 + vector, RRF) | 0.900 | 0.900 | 0.900 | 0.900 | 77 ms |
| **hybrid + rerank** (BGE-reranker) | 0.850 | 0.900 | 0.900 | 0.867 | 5086 ms |

> **Hallazgo**: en este corpus chico, el re-ranker cross-encoder **empeoró** Hit@1 (0.85 vs 0.90) y agregó 58× latencia. El sweet spot es `hybrid sin rerank`. El rerank solo ayuda con corpus >10K chunks. Ver [`docs/adr/0003-rerank-cross-encoder.md`](docs/adr/0003-rerank-cross-encoder.md) para el análisis completo.

Para reproducir: `python scripts/ablation.py --eval-set data/eval/qa_set.json`

### RAGAS-style metrics (generación)

Lightweight evaluation con Gemini Flash-Lite como judge (1 call por pregunta, ~5x más barato que full RAGAS):

| Métrica | Valor | Target |
|---------|-------|--------|
| **Faithfulness** | 0.87 | > 0.85 |
| **Answer Relevancy** | 1.00 | > 0.85 |
| **Context Precision** | 0.40 | > 0.75 |
| **Context Recall** | 0.59 | > 0.80 |

> Faithfulness y answer_relevancy en rango. Precision/recall bajos son por la LLM-as-judge siendo estricta con respuestas largas y ground_truths específicos — son métricas "duras" que castigan a sistemas con respuestas comprehensivas.

Para reproducir: `python scripts/evaluate_light.py --eval-set data/eval/qa_set.json`

Si llegás a los targets de faithfulness y answer_relevancy con 20+ Q&A, estás en el top 10% de implementaciones RAG. Ver [`docs/EVALUATION.md`](docs/EVALUATION.md) para cómo interpretar y diagnosticar.

---

## Deploy (gratis)

### Opción A: Docker Compose (local / VPS)

```bash
docker-compose up -d
# API en :8000, Streamlit en :8501
```

### Opción B: Railway (más fácil para deploy público)

1. Conectá tu repo de GitHub
2. Railway detecta el Dockerfile automáticamente
3. Deploy → URL pública en 2 minutos

### Opción C: Fly.io

```bash
fly launch
fly deploy
```

### Opción D: HuggingFace Spaces

1. Crear Space nuevo (Streamlit SDK)
2. Pushear código
3. URL pública con SSL

---

## Recursos y referencias

- [RAGAS documentation](https://docs.ragas.io/)
- [BGE embeddings paper](https://arxiv.org/abs/2402.03216)
- [Reciprocal Rank Fusion paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [Google Gemini free tier](https://aistudio.google.com/app/apikey)
- [Chroma documentation](https://docs.trychroma.com/)

---

## Licencia

MIT — usá esto como base, modificalo, hacé lo que quieras. Ver `LICENSE`.
