# A2 — Retrieval correcto

## Contexto

`BM25Store.query` no filtra por `collection` al cargar pickle. Hybrid/pipeline no propagan collection. Rerank activo por default (`top_k_rerank=5`): skip mal implementado puede devolver **lista vacía**. Metadata `None` rompe Chroma. Logs de ingest hardcodean “Chroma”.

## Toca

- `app/core/bm25_store.py`
- `app/core/hybrid_search.py`
- `app/core/pipeline.py`
- `app/core/reranker.py`
- `app/core/chunker.py` (si metadata/collection)
- `app/core/vector_store.py`
- `app/core/vector_store_databricks.py` (sanitizar metadata)
- `app/config.py` flags rerank (`ENABLE_RERANK` y/o `TOP_K_RERANK`)

## No toca

README, eval, Docker, generator, Streamlit, CI.

## Comportamiento

- `BM25Store.query(..., collection=)` carga el pickle y consulta **esa** colección.
- Hybrid + pipeline pasan `collection` a BM25 y vector store.
- `ENABLE_RERANK` default **false** **o** `TOP_K_RERANK=0`: no instanciar/llamar CrossEncoder; devolver top-k híbrido (**nunca** lista vacía).
- Sanitizar metadata `None` antes de upsert Chroma (y Databricks equivalente).
- Log de ingest: backend real (`chroma` / `databricks`), no string fijo “Chroma”.

## AC verificables

- [ ] `query(..., collection=)` en BM25 usa el índice persistido de esa collection.
- [ ] Hybrid y pipeline reenvían `collection`.
- [ ] Con rerank off / `TOP_K_RERANK=0`: mismos ids/order que fusión híbrida top-k; lista no vacía si el híbrido no lo está.
- [ ] Chunks con `metadata` value `None` no fallan en Chroma.
- [ ] Logs de ingest no asumen Chroma si el backend es otro.
- [ ] Default rerank opt-in (false o k=0).

## Riesgos

- Pickle multi-collection mal versionado.
- Skip que recorta a 0 por `[:0]`.
- Databricks metadata API distinta a Chroma.
