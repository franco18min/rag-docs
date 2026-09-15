# ADR-003: Cross-encoder rerank (BGE-reranker-base) en el pipeline

## Estado
Aceptado condicionalmente (2026-08-26)

## Contexto
Después del retrieval híbrido, los top-K (default 20) candidatos se re-rankean con un cross-encoder (BGE-reranker-base) que codifica `(query, document)` juntos en una sola pasada. Esto captura matices que el bi-encoder (BGE-M3) pierde.

## Decisión
**Rerank incluido en el pipeline, pero opt-in (`ENABLE_RERANK` default `False`).**

```python
# Habilitar rerank (desactivado por defecto)
ENABLE_RERANK=true
TOP_K_RERANK=5
RERANKER_MODEL=BAAI/bge-reranker-base
```

## Razones a favor
1. **Mejor precisión en queries ambiguos**: cross-encoder puede distinguir "Time Travel" (feature de Delta Lake) de "viaje en el tiempo" (literal).
2. **Re-ranking con negaciones**: bi-encoder no modela bien "no es X" vs "es X".
3. **Estado del arte en MS MARCO**: BGE-reranker-base logra MRR@10 = 0.365 en MS MARCO, comparable a modelos 10x más grandes.

## Ablación
Ver `scripts/ablation.py`. Para nuestro corpus de 18 chunks:

| Configuración | Hit@1 | Hit@3 | Latencia |
|--------|-------|-------|----------|
| hybrid sin rerank | 0.900 | 0.900 | 77ms |
| hybrid + rerank | 0.850 | 0.900 | 5086ms |

**El rerank empeoró Hit@1** en nuestro corpus. Por qué:

- Con 18 chunks, el top-1 de hybrid ya era casi siempre correcto.
- El cross-encoder reordena basándose en patrones del modelo (entrenado en MS MARCO, no en docs técnicos en español).
- 1 pregunta que estaba en top-1 sin rerank cayó a top-3 con rerank (score penalizado por alguna palabra técnica).

## Cuándo SÍ ayuda
- Corpus > 10K chunks donde la primera respuesta de vector denso es ruido.
- Queries multi-lenguaje donde el bi-encoder pierde precisión.
- Cuando el costo de re-ranking (2-5s) es aceptable para la latencia objetivo.

## Consecuencias
- **Positivas**: mejor precisión en el caso general (corpus grande, queries complejas).
- **Negativas**: 50x más latencia. En CPU, 5s por query. No viable para UX de tiempo real sin GPU.
- **Mitigación**: en producción se sirve el rerank con GPU. Para demo local, se puede desactivar vía `TOP_K_RERANK=0` (omitir) o `RERANKER_MODEL=` (vacío).

## Experimentos pendientes
- Evaluar con corpus sintético de 1000+ chunks para ver cuándo el rerank empieza a pagar.
- Probar alternativas: LLM-based rerank (Cohere Rerank, Jina Rerank) — más costoso pero más preciso.
