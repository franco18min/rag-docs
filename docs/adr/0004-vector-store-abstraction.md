# ADR-004: Vector store vendor-agnostic (Chroma dev / Databricks prod)

## Estado
Aceptado (2026-08-26)

## Contexto
El sistema necesita indexar embeddings en algún vector store. Opciones:

| Opción | Pros | Contras |
|--------|------|---------|
| **Chroma** | Open-source, simple, corre local, sin costo | No escala a >100K vectores eficientemente |
| **Databricks Vector Search** | Nativo de Databricks, Delta sync automático, $0.50/hr endpoint | Requiere workspace de Databricks, latencia de provisioning |
| **Pinecone / Weaviate / Qdrant** | Managed, escalables, baja latencia | Costo mensual, vendor lock-in, datos fuera de VPC |

## Decisión
**Abstracción con dos backends: Chroma (dev) y Databricks Vector Search (prod)**, seleccionados por `VECTOR_STORE_BACKEND` env var.

```python
# app/core/store_factory.py
def get_vector_store():
    if settings.vector_store_backend == "databricks":
        return DatabricksVectorStore()
    return VectorStore()  # Chroma
```

## Razones
1. **Dev experience**: la mayoría del desarrollo ocurre local sin Databricks. Chroma arranca en 2 segundos.
2. **Production-grade**: Databricks Vector Search ofrece Delta sync, governance con Unity Catalog, IAM via el workspace.
3. **Mismo interface**: `add()`, `query()`, `list_collections()` en ambos. El pipeline no sabe cuál está usando.
4. **Test-friendly**: los tests usan Chroma (in-memory) sin credenciales de Databricks.
5. **Costo cero en dev**: Chroma corre sin servicios externos.

## Trade-offs
- **Costo de mantener dos adapters**: ~200 líneas de código duplicado. Aceptable porque los backends son estables.
- **Tests deben correr contra ambos**: el smoke test corre contra Databricks; los pytest unitarios contra Chroma.
- **Data migration**: si cambias de backend, hay que re-ingestar. Aceptable porque ingest es 5-10 min.

## Consecuencias
- **Positivas**: dev sin fricción, deploy validado, sin vendor lock-in a nivel de aplicación.
- **Negativas**: las features específicas de un backend (por ej. filtros nativos en Databricks) no se exponen uniformemente.
- **Mitigación**: el `query()` acepta `where: dict` que ambos backends interpretan como filter (Databricks nativo, Chroma via `where` clause).

## Cuándo reconsiderar
- Si el corpus supera 10M vectores: considerar Milvus o Pinecone (no soportados hoy).
- Si el equipo decide consolidar todo en Databricks: remover Chroma del adapter factory.
