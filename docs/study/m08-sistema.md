# Módulo 8 — El RAG como producto (API, config, CI)

**Tiempo:** 40–60 min. **Prerrequisito:** haber corrido `/query` (módulo 1).

```
Estoy en el módulo 8 (docs/study/m08-sistema.md).
Quiero ver knobs y la factory del vector store. No empieces el experimento 9.
```

---

## Hoy te quiero dejar viendo un servicio, no un notebook

Un `pipeline.py` sin HTTP, tests ni config centralizada es un spike.
Este repo ya tiene la piel de producto mínima.

---

## Paso 1 — Dónde están los knobs

`app/config.py` (Pydantic Settings): chunk size, overlap, modelos,
`VECTOR_STORE_BACKEND`, `ENABLE_RERANK`, top-k, collection, API key.

Cambiar comportamiento **sin** cazar constantes mágicas en cinco
archivos: mismo instinto que un `job.yml`.

---

## Paso 2 — Superficies

| Superficie | Archivo | Rol |
|---|---|---|
| HTTP | `app/main.py` | `/health`, collections, `/query`, ingest |
| UI | `app/streamlit_app.py` | demo; misma lógica de pipeline |
| Tests | `tests/test_api.py`, `test_pipeline_query.py` | contratos |
| CI | `.github/workflows/ci.yml` | ruff + mypy + pytest |
| Observabilidad | `app/observability/` | **vacío**; `trace_id` es `None` |

`RAGPipeline` acepta dependencias por constructor: los tests inyectan
fakes. Equivale a mockear SparkSession.

---

## Paso 3 — Vendor-agnostic store

`store_factory.get_vector_store()` lee `VECTOR_STORE_BACKEND`:
`chroma` (default) o `databricks`.

Un tercer backend significaría implementar la **misma interfaz** que
`VectorStore` (add, query, delete, list, count), no “instalar
pgvector”: **no está** en el repo. ADR 0004.

Deploy opcional: `docs/DEPLOY_DATABRICKS.md`.

---

## Parada 8

Corpus 10× más grande (mismos tipos de doc). ¿Qué tocarías primero y
por qué: `chunk_size`, `top_k`, backend, rerank, o el eval set?

No hay una sola respuesta correcta; quiero tu razonamiento de DE
(costo, recall, ops).

---

## Laboratorio 8

1. Listá 5 settings de `config.py` y qué módulo del curso los cubrió.
2. Leé `store_factory.py` (es corto).
3. Abrí `ci.yml` y anotá qué se corre en cada push.

---

## Criterio para pasar al módulo 9

- [ ] Encontrás los knobs sin grep de valores mágicos.
- [ ] Explicás cómo agregarías (en diseño) un backend más.
- [ ] Sabés qué no hay: Langfuse, pgvector, RAGAS full.

```
Cierre módulo 8: para 10× corpus yo tocaría … porque …
Listo para el módulo 9.
```
