# Charter — RAG Docs (Specify)

## Tesis

MVP **evaluado**, no production-grade. Demo reproducible + retrieval correcto + citas ancladas + métricas honestas + CI que falla de verdad + README alineado. No es producto de plataforma.

## Stack (código en inglés)

FastAPI, Streamlit, BGE-M3, Chroma (dev) / Databricks Vector Search (opcional), BM25 + RRF, rerank CrossEncoder **opt-in**, Gemini Flash-Lite.

## Fuera de alcance

Langfuse real, streaming de tokens, memoria conversacional, pgvector, RAGAS full, corpus 50–100 docs, A8 deploy sin credenciales.

## Orden de implementación

Specify → A1 + A2 + A3 → A4 + A5 → A6 → A7 → A8 opcional.

| ID | Spec | Agente |
|----|------|--------|
| A1 | `001-reproducible-demo.md` | corpus + Quick Start + Gemini default |
| A2 | `002-retrieval-correctness.md` | BM25 collection, hybrid, rerank skip, metadata |
| A3 | `003-grounded-citations.md` | `[#N]` + parseo de citas |
| A4 | `004-evaluation-honesty.md` | `expected_source`, ablation, tablas honestas |
| A5 | `005-quality-gates.md` | tests + CI ruff/mypy reales |
| A6 | `006-portfolio-surface.md` | README/docs/Docker/CORS/health |
| A7 | (fuera de este lote Specify) | polish residual |
| A8 | opcional | deploy Databricks con credenciales |

## Principio

Promesas = lo que corre. Código de producto en inglés; specs y README de portfolio en español donde ya lo están.
