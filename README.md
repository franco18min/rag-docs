# 📚 RAG Docs — Sistema de Preguntas y Respuestas sobre Documentación Técnica

> Un sistema RAG (Retrieval-Augmented Generation) production-grade que ingiere documentación técnica, la indexa con búsqueda híbrida, y responde preguntas con citas a las fuentes. **Costo total: USD 0** usando Google Gemini, BGE-M3 y Chroma (dev) / Databricks Vector Search (deploy).

![Status](https://img.shields.io/badge/status-MVP%20working-success)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Stack](https://img.shields.io/badge/stack-100%25%20gratis-success)
![Deploy](https://img.shields.io/badge/Databricks%20Free%20Edition-validated-blue)

---

## 🎯 ¿Por qué este proyecto?

Este es el **Proyecto 1** del roadmap de transición de Data Engineer a AI Engineer. Demuestra:

- ✅ Diseño de pipelines de ingestión (transferible desde data engineering)
- ✅ Búsqueda híbrida (BM25 + vector denso) con re-ranking
- ✅ Evaluación sistemática (faithfulness, context recall, answer relevancy)
- ✅ Observability end-to-end (interface lista para Langfuse)
- ✅ Deploy production-grade con FastAPI + Docker
- ✅ **Backend vendor-agnostic**: Chroma (local) ↔ Databricks Vector Search (prod)
- ✅ **Deploy validado en Databricks Free Edition** (smoke test + retrieval eval 5/5)
- ✅ **Costo de inferencia: USD 0** (Gemini Flash-Lite free tier)

**Talking point para entrevistas:**
> *"Construí un sistema RAG sobre documentación técnica con búsqueda híbrida, re-ranking cross-encoder, y evaluación sistemática sobre un set de Q&A con ground truth. La pipeline corre 100% en free tiers (Gemini Flash-Lite, BGE-M3 local, Chroma dev / Databricks Vector Search prod). El deploy en Databricks Free Edition está validado end-to-end con smoke test, retrieval eval 5/5, y un RAGAS-style eval que muestra faithfulness 0.87 y answer_relevancy 1.0."*

Para más detalles sobre arquitectura, evaluación y talking points de entrevista, ver:
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — decisiones técnicas y trade-offs
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — cómo interpretar las métricas
- [`docs/INTERVIEW_TALKING_POINTS.md`](docs/INTERVIEW_TALKING_POINTS.md) — cómo presentar el proyecto
- [`docs/DEPLOY_DATABRICKS.md`](docs/DEPLOY_DATABRICKS.md) — setup Free Edition, gotchas y cleanup

---

## 🏗️ Arquitectura

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

## 🛠️ Tech Stack (todo gratis)

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

## ⚡ Quick Start (10 minutos al primer query)

### 1. Setup

```bash
# Clonar / descargar
cd "C:\Users\magna\Downloads\RAG Docs"

# Crear entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt

# Configurar API key de Gemini (gratis)
# Obtené tu key en https://aistudio.google.com/app/apikey
cp .env.example .env
# Editá .env y poné tu GOOGLE_API_KEY
```

### 2. Ingerir documentos

```bash
# Bajate un PDF o Markdown a data/raw/ primero
# Por ejemplo: la doc de Spark, dbt, Databricks, lo que conozcas

# Ingerir (rebuild=True si querés empezar de cero)
python -m scripts.ingest --source ./data/raw --collection spark_docs
```

Vas a ver: chunking → embedding → indexing. Cuando termine: `🎉 Ingest complete: 247 chunks from 8 documents in 12.4s`.

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

## 📁 Estructura del proyecto

```
rag-docs/
├── README.md                      # Este archivo
├── requirements.txt               # Dependencias
├── .env.example                   # Template de variables de entorno
├── .gitignore
├── LICENSE                        # MIT
├── Dockerfile                     # Para deploy
├── docker-compose.yml             # API + Streamlit
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
│   │   ├── bm25_store.py          # rank-bm25 wrapper (persistido)
│   │   ├── hybrid_search.py       # Búsqueda híbrida con RRF
│   │   ├── reranker.py            # Cross-encoder re-ranking
│   │   ├── generator.py           # Gemini wrapper con prompt estructurado
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
│   └── evaluate.py                # RAGAS evaluation runner
│
├── data/                          # Data local (no commitear — ver .gitignore)
│   ├── raw/                       # PDFs/MDs originales
│   ├── chroma/                    # Vector DB local
│   ├── processed/                 # (reservado)
│   └── eval/
│       ├── qa_set_template.json   # Template starter con 5 Q&A curadas
│       └── results.json           # (generado por evaluate.py)
│
├── tests/                         # Tests (pytest)
│   ├── test_chunker.py
│   ├── test_hybrid_search.py
│   └── test_pipeline_query.py
│
└── docs/                          # Documentación adicional
    ├── ARCHITECTURE.md            # Decisiones técnicas detalladas
    ├── EVALUATION.md              # Cómo interpretar métricas RAGAS
    └── INTERVIEW_TALKING_POINTS.md  # Cómo presentar el proyecto
```

---

## 📊 Features implementadas

### Core (MVP) — ✅ listo y funcionando
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
- [x] Documentación: ARCHITECTURE, EVALUATION, INTERVIEW_TALKING_POINTS

### Avances (post-MVP) — próximos pasos
- [ ] Instrumentación con Langfuse (interface lista en `QueryResponse.trace_id`)
- [ ] Cache de queries frecuentes (Redis layer)
- [ ] Streaming de respuestas (Gemini lo soporta)
- [ ] Conversational memory (multi-turn)
- [ ] A/B testing de prompts
- [ ] Migración a pgvector
- [ ] CI/CD con GitHub Actions
- [ ] Monitoring de costos / usage

---

## 🎯 Datasets sugeridos para arrancar

Elegí uno que conozcas bien — el dominio importa para evaluar la calidad de las respuestas.

| Dataset | Cuándo usarlo | Tamaño |
|---|---|---|
| **Apache Spark docs** (EN) | Si querés mostrar dominio de big data | ~200 páginas |
| **dbt documentation** (EN) | Si querés mostrar dominio de transformaciones | ~150 páginas |
| **Databricks docs** (EN) | Si te interesa lakehouse (tu fuerte) | ~300 páginas |
| **AFIP / BCRA normativa** (ES) | Si querés diferenciarte con dominio local argentino | ~100-200 PDFs |
| **Manzur docs internos** | Si tenés acceso y querés algo real (cuidado con NDA) | Variable |
| **Hadoop / Kafka docs** | Si querés ir a fundamentals | ~250 páginas |

**Mi recomendación para vos:** arrancá con **Databricks docs** porque es donde más fuerte está tu background (Delta Lake, Medallion, Spark), y eso se nota cuando evaluás las respuestas.

---

## 📈 Métricas de evaluación (RAGAS)

Cuando corras la evaluación, apuntá a estos números:

| Métrica | Qué mide | Target |
|---|---|---|
| **Faithfulness** | ¿La respuesta es fiel al contexto recuperado? | > 0.85 |
| **Context Precision** | ¿Los chunks recuperados son relevantes? | > 0.75 |
| **Context Recall** | ¿Estamos recuperando toda la info necesaria? | > 0.80 |
| **Answer Relevancy** | ¿La respuesta es relevante a la pregunta? | > 0.85 |

Si llegás a esos números con 30+ preguntas, estás en el top 10% de implementaciones RAG. Ver [`docs/EVALUATION.md`](docs/EVALUATION.md) para cómo interpretar resultados y diagnosticar problemas.

---

## 🚀 Deploy (gratis)

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

## 🎤 Talking points para entrevistas

Ver [`docs/INTERVIEW_TALKING_POINTS.md`](docs/INTERVIEW_TALKING_POINTS.md) para la guía completa. Resumen:

- **30s pitch**: "RAG production-grade sobre docs técnicas con búsqueda híbrida, re-ranking cross-encoder, evaluación RAGAS, free tier."
- **Lección clave**: "La diferencia entre un RAG de tutorial y uno de producción es la evaluación sistemática. Medir, iterar, medir."
- **Por qué híbrida**: "Dense embeddings capturan semántica, BM25 captura exact match. Son complementarios en docs técnicas."
- **Por qué re-ranking**: "Cross-encoder es ~100x más preciso pero ~100x más lento. Patrón: bi-encoder top-20 → cross-encoder top-5."

---

## 📚 Recursos y referencias

- [RAGAS documentation](https://docs.ragas.io/)
- [BGE embeddings paper](https://arxiv.org/abs/2402.03216)
- [Reciprocal Rank Fusion paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [Google Gemini free tier](https://aistudio.google.com/app/apikey)
- [Chroma documentation](https://docs.trychroma.com/)

---

## 🛣️ Roadmap personal

### Semana 1-2: MVP básico ✅
- [x] Setup del entorno + ingesta
- [x] Pipeline simple: query → retrieve → generate
- [x] API funcionando con curl

### Semana 2-3: Mejoras de retrieval ✅
- [x] Búsqueda híbrida BM25 + vector con RRF
- [x] Re-ranking con cross-encoder
- [x] Chunking con metadata rica

### Semana 3-4: Evaluación y observability ✅ (parcial)
- [x] Set de Q&A auto-generable con Gemini
- [x] RAGAS runner con 4 métricas
- [x] Tests unitarios
- [x] Documentación completa
- [ ] Langfuse self-hosted (interface lista, falta wire-up)

### Semana 4: Polish y deploy 🟡
- [x] UI Streamlit funcional
- [x] Docker + docker-compose
- [ ] Deploy público (Railway / HF Spaces)
- [ ] Video demo de 2 minutos

---

## 📄 Licencia

MIT — usá esto como base, modificalo, hacé lo que quieras. Ver `LICENSE`.

---

## 🙋 Sobre el autor

**Franco Aguilera** — Data Engineer en transición a AI Engineer. Jujuy, Argentina.

- LinkedIn: [linkedin.com/in/franco-aguilera-data-engineer](https://linkedin.com/in/franco-aguilera-data-engineer)
- GitHub: [github.com/franco18min](https://github.com/franco18min)
- Email: magnagg@gmail.com

Construyendo este proyecto como parte de un plan de 6 meses para transicionar de Data Engineering a AI Engineering. Stack: Python, SQL, PySpark, AWS, Databricks, ahora aprendiendo RAG, LLM APIs, y AI evaluation.
