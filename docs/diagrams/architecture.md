# RAG Docs — Diagrama de arquitectura

Vista visual del sistema. Dos partes:
1. **Alto nivel**: qué es RAG, en 30 segundos
2. **Detalle**: cómo este proyecto implementa cada paso

## Alto nivel: dos fases, un store compartido

```
                          RAG: dos fases, un store
                          ========================

  OFFLINE (una vez)                   ONLINE (cada pregunta)
  =================                   ====================

  Doc → Chunk → Embed ──┐              ┌──▶  Vector Search ──┐
                        │              │                     │
                        ├──────────────┤   hybrid con BM25   ├──▶ Rerank?──▶ LLM ──▶ Answer
                        │              │                     │    (cross-    (Gemini    + Citations
                        │              └──▶  BM25 keyword ──┘    encoder)    Flash-Lite)
                        ▼
                  [Vector Store]
                  Chroma | Databricks VS
```

**Idea clave:** los mismos datos (chunks + embeddings) se usan para escribir (offline) y para buscar (online). La pipeline se monta sobre ese store compartido.

## Detalle: cada caja

```
                  RAG: Retrieval-Augmented Generation
                  =====================================

  ┌──────────────────── OFFLINE (una vez) ─────────────────────┐
  │                                                             │
  │   ┌──────────┐   ┌──────────┐   ┌──────────┐               │
  │   │Documents │──▶│ Chunker  │──▶│ Embedder │               │
  │   │PDF/MD/   │   │ 512 tok  │   │ BGE-M3   │               │
  │   │HTML/TXT  │   │ 64 over- │   │ 1024-dim │               │
  │   │          │   │ lap      │   │ per chunk│               │
  │   └──────────┘   └──────────┘   └────┬─────┘               │
  │                                      │                      │
  │                                      ▼                      │
  │                          ┌──────────────────────┐           │
  │                          │    Vector Store      │           │
  │                          │                      │           │
  │                          │  dev: Chroma         │           │
  │                          │       (in-process)   │           │
  │                          │                      │           │
  │                          │  prod: Databricks    │           │
  │                          │       Vector Search  │           │
  │                          │   (Delta table +     │           │
  │                          │    vector index)     │           │
  │                          └──────────┬───────────┘           │
  │                                     │                       │
  └─────────────────────────────────────┼───────────────────────┘
                                        │
  ┌──────────────────── ONLINE (por query) ─┼──────────────┐
  │                                     │               │
  │   ┌──────────┐                     │               │
  │   │ Question │                     │               │
  │   └────┬─────┘                     │               │
  │        │                            │               │
  │        ▼                            │               │
  │   ┌──────────┐                     │               │
  │   │  Embed   │   (mismo BGE-M3)   │               │
  │   │  query   │                     │               │
  │   └────┬─────┘                     │               │
  │        │                            │               │
  │        ▼                            │               │
  │   ┌────────────────────────────────┘               │
  │   │  Vector Search (cosine top-K)  ◀── lee el índice
  │   │           +  BM25 keyword
  │   │           =  RRF fusion
  │   └────────────┬───────────────────┘
  │                │
  │                ▼
  │   ┌────────────────┐
  │   │   Reranker     │  (BGE-reranker, opcional)
  │   └────────┬───────┘
  │            │
  │            ▼
  │   ┌────────────────┐
  │   │      LLM       │  Gemini Flash-Lite
  │   │  + context    │  "Respondé SOLO con
  │   │  + question   │   este contexto..."
  │   └────────┬───────┘
  │            │
  │            ▼
  │   ┌────────────────┐
  │   │  Answer +      │
  │   │  Citations     │  (texto + paths de source)
  │   └────────────────┘
  │
  └─────────────────────────────────────────────────────────┘
```

## Versión Mermaid (se renderiza en GitHub)

```mermaid
flowchart TB
    subgraph offline["Offline: ingestión (una vez)"]
        A[Documents<br/>PDF/MD/HTML/TXT] --> B[Chunker<br/>512 tok + 64 overlap]
        B --> C[Embedder<br/>BGE-M3 1024-dim]
        C --> D[Vector Store<br/>Chroma or Databricks VS]
    end

    subgraph online["Online: query (por pregunta)"]
        E[Question] --> F[Embed query<br/>mismo BGE-M3]
        F --> G[Vector Search<br/>top-K by cosine]
        G --> H[Reranker opt-in<br/>BGE-reranker cross-encoder]
        H --> I[LLM<br/>Gemini Flash-Lite]
        I --> J[Answer + Citations]
    end

    D -. índice compartido .-> G

    K[BM25<br/>keyword search] --> G

    style D fill:#fff4cc,stroke:#333
    style J fill:#d4f4dd,stroke:#333
```

## Cómo leerlo en una entrevista

Cuando expliques RAG a un recruiter no técnico o a un par, usá el diagrama de
**alto nivel** (el primero). Recorrélo de izquierda a derecha, de arriba abajo:

1. "Tomamos documentos, los partimos en chunks y convertimos cada chunk a un vector numérico."
2. "Cuando el usuario pregunta, convertimos la pregunta de la misma forma."
3. "Buscamos en el store vectores similares al vector de la pregunta."
4. "Pasamos los top chunks más la pregunta a un LLM."
5. "El LLM responde usando solo los chunks que encontramos, y citamos las fuentes."

Para una entrevista de ingeniería de AI, sumá:
- "Usamos búsqueda híbrida (BM25 + vector) fusionada con RRF porque el vector falla en keywords exactas."
- "El rerank con cross-encoder es opt-in (`ENABLE_RERANK`); el default es off después de la ablation en este corpus."
- "Elegimos BGE-M3 por soporte multilingüe y deploy on-prem."
- "Separamos Chroma (dev) y Databricks (prod) detrás de una sola interfaz."

## Ver también

- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — versión en texto completo
- [`docs/adr/0004-vector-store-abstraction.md`](../adr/0004-vector-store-abstraction.md) — por qué hay dos backends
- [`docs/adr/0002-hybrid-search-bm25-vector.md`](../adr/0002-hybrid-search-bm25-vector.md) — búsqueda híbrida
