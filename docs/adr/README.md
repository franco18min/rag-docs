# ADRs (registros de decisión de arquitectura)

Decisiones de diseño documentadas con su contexto, opciones consideradas y compromisos.

| # | Decisión | Estado |
|---|----------|--------|
| [001](0001-bge-m3-embedding-model.md) | BGE-M3 como modelo de embedding | Aceptado |
| [002](0002-hybrid-search-bm25-vector.md) | Búsqueda híbrida (BM25 + vector) con RRF | Aceptado |
| [003](0003-rerank-cross-encoder.md) | Cross-encoder rerank (BGE-reranker-base) | Aceptado condicionalmente |
| [004](0004-vector-store-abstraction.md) | Vector store vendor-agnostic (Chroma / Databricks) | Aceptado |
| [005](0005-gemini-flash-lite.md) | Gemini Flash-Lite como generador | Aceptado |

## Formato

Cada ADR sigue el formato de Michael Nygard:
- **Estado**: Aceptado / Propuesto / Deprecado / Reemplazado
- **Contexto**: el problema a resolver
- **Decisión**: lo que hicimos
- **Razones**: por qué
- **Consecuencias**: compromisos y mitigaciones
- **Cuándo reconsiderar**: señales de que la decisión debe revisarse

Las ADRs son inmutables una vez aceptadas. Si una decisión cambia, se escribe una nueva ADR que la reemplaza (marcando la anterior como "Reemplazado").
