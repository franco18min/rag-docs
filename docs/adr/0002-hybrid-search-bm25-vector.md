# ADR-002: Búsqueda híbrida (BM25 + vector denso) con Reciprocal Rank Fusion

## Estado
Aceptado (2026-08-26)

## Contexto
Un sistema RAG depende de la calidad del retrieval. Dos familias principales:

- **Vector denso (BGE-M3)**: captura semántica y sinonimia pero falla en keywords raros, IDs de error, acrónimos exactos.
- **BM25 (keyword)**: exacto, rápido, sin dependencias, pero pierde sinonimia ("ML" vs "machine learning").

La elección es uno solo o combinarlos.

## Decisión
**Híbrido con RRF (Reciprocal Rank Fusion)**.

```python
score(d) = sum(1 / (k + rank_i(d)))  para cada retriever i
```

donde `k=60` (default Cormack et al. SIGIR 2009).

## Razones
1. **Complementarios**: BM25 captura "Delta Lake" exacto, el vector captura "lago delta" o "storage layer". Combinarlos cubre ambos casos.
2. **Sin calibración**: RRF opera sobre rangos (no scores absolutos), eliminando el problema de comparar cosine similarity (0-1) con BM25 score (0-∞).
3. **Bien estudiado**: paper de Cormack et al. en SIGIR 2009 muestra que RRF supera a métodos más complejos de rank aggregation.
4. **Costo bajo**: BM25 es CPU-only y <10ms por query. El costo agregado es despreciable.

## Ablation
Ver `scripts/ablation.py` con 20 Q&A del corpus. Resultados sobre 18 chunks (corpus pequeño):

| Configuración | Hit@1 | Hit@3 | Hit@5 | Latencia |
|---------------|-------|-------|-------|----------|
| vector-only | 0.900 | 0.900 | 0.900 | 88ms |
| hybrid (BM25+vector, RRF) | 0.900 | 0.900 | 0.900 | 77ms |
| hybrid + rerank (full stack) | 0.850 | 0.900 | 0.900 | 5086ms |

Para corpus pequeños, BM25 + vector es indistinguible de vector solo (el corpus es tan chico que casi todo es top-1). El rerank agregó latencia 58x y **empeoró** Hit@1.

## Consecuencias
- **Positivas**: cobertura más amplia de queries. Robusto ante typos y reformulaciones.
- **Negativas**: dos índices que mantener sincronizados (vector + BM25 pickle). Más complejidad en CI.
- **Mitigación**: el `HybridSearch` reusa el `VectorStore` para query y solo agrega un BM25 en memoria. La sincronización se hace en `ingest()` después del `vector_store.add()`.

## Cuándo reconsiderar
Si el corpus supera ~50K chunks y los queries son mayoritariamente keyword (ej: "ERROR XYZ1234"), conviene evaluar ColBERT o BM25-only.
