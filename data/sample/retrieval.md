# Retrieval: RRF y chunking

## Reciprocal Rank Fusion (RRF)

Reciprocal Rank Fusion es un método de agregación de rankings que combina listas de diferentes retrievers (BM25 y vector denso) sin requerir calibración de scores. La fórmula es RRF_score(d) = sum(1 / (k + rank_i(d))) para cada retriever i. Es simple, bien estudiada (paper Cormack et al. SIGIR 2009) y robusta. El parámetro k (típicamente 60) suaviza la contribución de ranks altos.

## Chunking 512 / 64

El chunker por defecto produce chunks de 512 tokens con 64 tokens de overlap (configurable vía CHUNK_SIZE y CHUNK_OVERLAP en settings). El overlap existe para que un concepto que cruza el límite entre dos chunks no se pierda: si una oración empieza en el chunk 1 y termina en el chunk 2, el overlap asegura que ambos chunks la contengan y la pregunta del usuario pueda matchear con cualquiera de los dos.
