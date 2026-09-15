# A6 — Superficie de portfolio

## Contexto

README dice production-grade, corpus 50–100, pgvector/path magna, Langfuse, RAGAS full, deploy “validated”. `ARCHITECTURE.md` cita `tracing.py`. `DEPLOY_DATABRICKS` host real. Comentarios a archivos inexistentes. Sin `.dockerignore`. CORS + credentials. `/health` carga pipeline pesado.

## Toca

- `README.md` (resto; Quick Start ya A1)
- `docs/ARCHITECTURE.md`, `docs/DEPLOY_DATABRICKS.md`, `docs/diagrams/**`
- ADRs si contradicen el charter
- Docker / `docker-compose.yml` / `.dockerignore`
- `app/observability/**`
- CORS y health en `app/main.py` **coordinado con A3** (no parser de citas)

## No toca

Parser de citas, retrieval core, `qa_set` honesty, tests/CI de A5.

## Mensajes README

- MVP **evaluado**, **no** production-grade.
- Stack: Databricks Vector Search opcional; **no** pgvector actual.
- Sin path magna.
- Langfuse **no implementado**.
- RAGAS full **no soportado**.

## Otros

- ARCHITECTURE: **sin** `tracing.py` como si existiera.
- DEPLOY: host **placeholder** (no workspace personal).
- Quitar comentarios que apuntan a archivos inexistentes.
- Añadir `.dockerignore`.
- CORS: `allow_credentials=false` **o** origins explícitos (no `*` + credentials).
- `/health` **sin** cargar pipeline/embedder/reranker.

## AC verificables

- [ ] README no dice production-grade / RAGAS full operativo / Langfuse vivo / pgvector / magna.
- [ ] ARCHITECTURE no referencia `app/observability/tracing.py`.
- [ ] DEPLOY host es placeholder.
- [ ] Existe `.dockerignore`.
- [ ] CORS cumple la regla credentials/origins.
- [ ] Health no instancia pipeline pesado (test o inspección).
- [ ] Diff no reescribe parser de citas.

## Riesgos

- A3 y A6 editan `main.py` → merge: health/CORS vs citas.
- Diagramas viejos (50–100 docs, rerank always-on).
