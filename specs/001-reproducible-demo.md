# A1 — Demo reproducible (corpus)

## Contexto

No hay `data/sample/**`. `qa_set.json` tiene `ground_truth` sobre Delta Lake, Medallion, Time Travel, Structured Streaming, persistencia Spark, Databricks Vector Search, BGE-M3 y retrieval (RRF + chunking). `GEMINI_MODEL` default es `gemini-2.0-flash-exp`. Quick Start incompleto para Unix+Windows.

## Toca

- `data/sample/**` (markdowns)
- `.env.example`
- `app/config.py` **solo** default Gemini
- `README.md` **solo** Quick Start

## No toca

Pipeline, generator, CI, métricas, eval scripts, Docker, retrieval.

## Entrega

Markdowns (nombres de archivo):

- `delta_lake_intro.md`
- `medallion_architecture.md`
- `delta_time_travel.md`
- `structured_streaming.md`
- `spark_persistence.md`
- `databricks_vector_search.md`
- `bge_m3.md`
- `retrieval.md` (RRF + chunking)

Contenido **reconstruido** desde `ground_truth` en `data/eval/qa_set.json` (hechos suficientes para que esas Q&A sean respondibles).

Default `GEMINI_MODEL=gemini-flash-lite-latest` en `app/config.py` y `.env.example`.

Quick Start Unix + Windows: ingest `--source ./data/sample --collection spark_docs`.

## AC verificables

- [ ] Existen los 8 `.md` bajo `data/sample/` con esos stems.
- [ ] Cada ítem de `qa_set.json` es cubierto por al menos un markdown (hechos del `ground_truth` presentes).
- [ ] `app/config.py`: default `gemini_model` = `gemini-flash-lite-latest`.
- [ ] `.env.example` declara `GEMINI_MODEL=gemini-flash-lite-latest`.
- [ ] README Quick Start: Unix y Windows; comando ingest con `--source ./data/sample --collection spark_docs`.
- [ ] Diff no incluye pipeline/generator/CI/métricas.

## Riesgos

- Corpus demasiado corto → retrieval “pasa” por coincidencia; A4 debe declarar corpus chico.
- Overfit al wording exacto del `ground_truth` (aceptable para demo).
