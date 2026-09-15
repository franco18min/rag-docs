# Arquitectura y decisiones técnicas

Este documento explica *por qué* el sistema está armado así: trade-offs
considerados, alternativas descartadas y elecciones de diseño que afectan
calidad, costo y mantenibilidad.

## Vista general del pipeline

```
                   ┌─────────────┐
                   │  Documentos │  PDF / Markdown / HTML / TXT
                   └──────┬──────┘
                          │ 1. Load (readers por formato)
                          ▼
                   ┌─────────────┐
                   │  Chunking   │  tiktoken, sliding window 512/64
                   └──────┬──────┘  con metadata rica
                          │ 2. Embed (BGE-M3, normalizado, 1024-dim)
                          ▼
              ┌───────────────────────┐
              │   Vector (Chroma)     │  cosine similarity
              │   +  BM25 index       │  match léxico exacto
              └──────────┬────────────┘
                         │ 3. Retrieval híbrido (top-20 cada uno)
                         ▼
              ┌─────────────────────┐
              │  RRF fusion         │  Reciprocal Rank Fusion, k=60
              └──────────┬──────────┘
                         │ 4. Rerank (opt-in; BGE-reranker, top-20 → top-5)
                         ▼
              ┌─────────────────────┐
              │  Gemini Flash-Lite  │  Respuesta grounded con citas [#N]
              └──────────┬──────────┘
                         │ 5. Response (answer + citations + scores)
                         ▼
                    {answer, citations, latency_ms, model}
```

## Decisiones clave

### 1. Búsqueda híbrida (BM25 + vector denso) con RRF

**¿Por qué no solo retrieval denso?**
Los embeddings andan bien para similitud semántica, pero se traban con
queries de match exacto. En documentación técnica la gente busca términos
concretos: nombres de función, códigos de error, flags de config, números
de versión. BM25 clava esos casos.

**¿Por qué RRF en vez de fusión ponderada de scores?**
Reciprocal Rank Fusion agrega rangos: no hace falta calibrar los scores
de los dos retrievers a la misma escala. Ese es el dolor operativo de la
fusión ponderada (los scores de BM25 no tienen cota; cosine similarity
vive en [-1, 1]).

Fórmula RRF:
```
rrf(d) = Σ_r 1 / (k + rank_r(d))
```
Usamos `k=60` (el valor del paper original de Cormack et al., SIGIR 2009).

**Trade-off**: dos retrievers implican dos índices y más memoria. A escala
de demo es despreciable. Con 10M+ chunks conviene consolidar en un índice
denso + filtro de keywords, o pasar a un motor híbrido nativo como
Weaviate o Qdrant.

### 2. Cross-encoder re-ranker encima del híbrido

**¿Por qué no saltearse el re-ranking?**
Los bi-encoders (BGE-M3) embeddean query y documento por separado: es
rápido, pero no capturan la interacción fina query↔documento.

Los cross-encoders (BGE-reranker-base) codifican el par junto y devuelven
un score de relevancia. Son ~10× más precisos en la cabeza del ranking,
pero ~100× más lentos: por eso solo los aplicamos al top-20 del híbrido
y devolvemos top-5.

Los papers publicados de BGE reranker reportan ganancias grandes de nDCG
en benchmarks públicos de IR. **Este repo no afirma un lift de +20–30%
nDCG** sobre el corpus de demo. La ablation local en 20 Q&A mostró que
Hit@1 baja con rerank y ~50× de latencia en CPU. Default:
`ENABLE_RERANK=false`.

**Trade-off**: el rerank es opt-in; habilitalo solo cuando el corpus y el
presupuesto de latencia justifiquen cargar el cross-encoder.

### 3. Sliding window 512/64

**¿Por qué 512 tokens?**
- Lo bastante largo para un concepto autónomo (un párrafo, un bloque de config)
- Lo bastante corto para mantener bajo el costo de embedding (BGE-M3 tiene
  contexto de 8K, pero la señal útil suele estar en los primeros 512 tokens)
- Alineado con el tamaño de chunk de la mayoría de tutoriales RAG, así
  al comparar números con benchmarks públicos comparamos peras con peras

**¿Por qué overlap de 64 tokens (~12.5%)?**
- Alto suficiente para que ningún límite semántico caiga en una zona
  muerta entre chunks
- Bajo suficiente para no multiplicar el índice por 8 a cambio de un
  recall marginal

**Alternativas consideradas**:
- **Split por oraciones** (NLTK, spacy) — pero los docs mezclan español e
  inglés y tienen muchos bloques de código, que rompen la detección de
  oraciones.
- **Chunking semántico** (cortar cuando baja la similitud de embedding) —
  demasiado lento en ingest para este corpus de demo, y en la práctica
  no se nota claramente mejor.

### 4. BGE-M3 (multilingüe, contexto largo)

**¿Por qué BGE-M3 frente a OpenAI `text-embedding-3-small`?**
- Corre local → sin costo por query, sin latencia de API
- Multilingüe (100+ idiomas, fuerte en español) — importante para nuestro caso
- Contexto largo (8K tokens) → se puede re-embeddear un chunk sin truncar

**Trade-off**: ~400MB de descarga, ~1GB de RAM, ~50ms por chunk en CPU.
Para 300 documentos × 5 chunks = 1500 chunks, el ingest lleva ~1.5 minutos.

### 5. Gemini Flash-Lite para generación

Id de modelo por default: `gemini-flash-lite-latest`.

**¿Por qué no GPT-4o / Claude?**
- El free tier (1,500 req/día) alcanza para corridas de evaluación y demos
- Rápido (~1s para respuestas de 500 tokens)
- Suficiente en Q&A técnico (no es state-of-the-art, pero >90% de GPT-4o
  en nuestro eval set)

**¿Por qué prompting estructurado?**
- Forzar al modelo a citar chunks con `[#N]` para mapear citas a fuentes
  recuperadas
- Camino explícito de "no sé" cuando el contexto no contiene la respuesta
  (evita alucinación)
- Temperatura baja (0.2) para respuestas grounded y deterministas

### 6. Chroma (dev) y Databricks Vector Search (opcional)

**¿Por qué Chroma para el MVP?**
- Cero ops, corre in-process, persiste a disco
- Interfaz delgada `VectorStore` compartida con el adapter de Databricks
- Permite enfocarnos en el pipeline, no en infraestructura

**Camino actual:** `VECTOR_STORE_BACKEND=chroma` (default) o `databricks`.
**No hay backend pgvector** en este repo.

**Cuándo Databricks aporta**:
- Demo contra Unity Catalog / Vector Search
- Necesidad de un índice remoto en vez de archivos locales de Chroma

## Qué NO está a propósito (todavía)

- **Respuestas en streaming**: Gemini lo soporta; nosotros devolvemos la
  respuesta completa. Fácil de agregar con
  `model.generate_content(..., stream=True)`.
- **Memoria conversacional**: cada query es independiente. Multi-turno
  necesita reformulación de query + retriever con historia.
- **Caché de queries frecuentes**: una capa Redis delante de `/query`
  bajaría la latencia a ~10ms en queries calientes.
- **A/B de prompts**: el prompt está en `generator.py`.
- **Langfuse / tracing distribuido**: no implementado.
  `QueryResponse.trace_id` es siempre `None`.
- **RAGAS full**: no soportado; usar `scripts/evaluate_light.py`.

## Grafo de dependencias de componentes

```
pipeline.py
├── chunker.py          (depends on: config, tiktoken)
├── embedder.py         (depends on: config, sentence-transformers)
├── vector_store.py     (depends on: config, chromadb)
├── bm25_store.py       (depends on: config, rank_bm25)
├── hybrid_search.py    (depends on: config, vector_store, bm25_store)
├── reranker.py         (depends on: config, sentence-transformers CrossEncoder)
└── generator.py        (depends on: config, google-generativeai)
```

Cada módulo de core se puede importar y testear por separado. El pipeline
acepta inyección de dependencias por constructor, así los tests pueden
cambiar fakes.
