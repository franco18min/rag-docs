# BGE-M3

BGE-M3 produce vectores dense de 1024 dimensiones, tiene ~568M parámetros, ocupa ~2.3GB en disco en FP32 (~1.1GB en FP16) y acepta hasta 8192 tokens de contexto, lo que lo hace adecuado tanto para queries cortas como para documentos largos.

## Cuándo conviene elegir BGE-M3 y cuándo NO

Conviene elegir BGE-M3 cuando necesitás soporte multi-idioma serio (español+inglés mezclado, 100+ idiomas), querés evitar vendor lock-in corriendo el modelo on-prem, o tu dataset tiene queries y documentos largos porque aguanta 8192 tokens. NO conviene cuando solo trabajás en inglés con latencia crítica (all-MiniLM-L6-v2 o bge-large-en son mejores), tenés acceso a OpenAI y preferís delegar el costo de GPU a un API, o el dataset es muy grande y querés embeddings baratos.

## Bi-encoder vs cross-encoder (re-ranking)

El bi-encoder (BGE-M3) codifica query y documento independientemente en vectores y compara por cosine similarity, lo cual es rápido pero pierde información de interacción. El cross-encoder (BGE-reranker) codifica query+documento juntos en una sola pasada, permitiendo atención cruzada token-a-token, lo que captura matices como negaciones, sinonimia contextual y orden de palabras. Por eso se usa como segundo paso: bi-encoder para top-20 candidatos rápido, cross-encoder para re-rankear a top-5 preciso.
