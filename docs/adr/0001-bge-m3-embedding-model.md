# ADR-001: BGE-M3 como modelo de embedding (en vez de OpenAI/Cohere)

## Estado
Aceptado (2026-08-26)

## Contexto
Necesitamos un modelo de embeddings para indexar chunks de documentación técnica en español e inglés. Tres candidatas evaluadas:

| Opción | Pros | Contras |
|--------|------|---------|
| **OpenAI text-embedding-3-small** | API, 1536 dims, $0.02/M tokens, sin GPU | Vendor lock-in, costo recurrente, datos salen del VPC |
| **Cohere embed-multilingual-v3** | API, 1024 dims, 100+ idiomas, gratis trial | Vendor lock-in, plan free restringido |
| **BGE-M3 (BAAI)** | Open-source, 1024 dims, 100+ idiomas, corre on-prem, gratis | Requiere ~3GB RAM/disk, inferencia más lenta que API |

## Decisión
**BGE-M3** local.

## Razones
1. **Multi-idioma nativo**: la documentación es mayoritariamente en español pero con términos en inglés (Delta Lake, Time Travel, Structured Streaming). BGE-M3 fue entrenado específicamente en 100+ idiomas con representación compartida.
2. **Sin vendor lock-in**: el modelo corre on-prem o en cualquier VM sin necesidad de credenciales. Cero costo marginal una vez descargado.
3. **Datos sensibles**: la documentación interna no necesita salir a una API externa. Cumple con cualquier política de data residency.
4. **Contexto largo (8192 tokens)**: soporta documentos largos sin truncar agresivamente. Mejor que los 512 tokens de BERT original.
5. **Reproducibilidad**: los embeddings son deterministas (sin dropout en inference), así que re-indexar produce el mismo vector.

## Consecuencias
- **Positivas**: costo total de embedding = 0 USD. Funciona offline. Sin rate limits.
- **Negativas**: ~30s para embed 18 chunks en CPU; ~5s en GPU. Inferencia más lenta que una API, pero aceptable para batch ingestion.
- **Mitigación**: el `Embedder` es un singleton que se cachea en memoria. Para 1000+ chunks/día se recomienda una GPU modesta (RTX 3090 hace 5-10 chunks/s).

## Notas
El primer download del modelo (~2.3GB) requiere acceso a huggingface.co sin auth (rate limit ~10 req/min). En entornos restringidos se puede pre-cachear el snapshot manualmente.
