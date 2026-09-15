# Architecture & Technical Decisions

This document explains *why* the system is built the way it is — the trade-offs
considered, the alternatives rejected, and the design choices that affect
quality, cost, and maintainability.

## Pipeline Overview

```
                   ┌─────────────┐
                   │  Documents  │  PDF / Markdown / HTML / TXT
                   └──────┬──────┘
                          │ 1. Load (per-format readers)
                          ▼
                   ┌─────────────┐
                   │  Chunking   │  tiktoken, sliding window 512/64
                   └──────┬──────┘  with rich metadata
                          │ 2. Embed (BGE-M3, normalized, 1024-dim)
                          ▼
              ┌───────────────────────┐
              │   Vector (Chroma)     │  cosine similarity
              │   +  BM25 index       │  lexical exact match
              └──────────┬────────────┘
                         │ 3. Hybrid retrieval (top-20 each)
                         ▼
              ┌─────────────────────┐
              │  RRF fusion         │  Reciprocal Rank Fusion, k=60
              └──────────┬──────────┘
                         │ 4. Rerank (opt-in; BGE-reranker, top-20 → top-5)
                         ▼
              ┌─────────────────────┐
              │  Gemini 2.0 Flash   │  Grounded answer with [#N] citations
              └──────────┬──────────┘
                         │ 5. Response (answer + citations + scores)
                         ▼
                    {answer, citations, latency_ms, model}
```

## Key Decisions

### 1. Hybrid search (BM25 + dense) with RRF

**Why not pure dense retrieval?**
Embeddings are great for semantic similarity but struggle with exact-match
queries. In technical documentation, users often search for specific terms:
function names, error codes, config flags, version numbers. BM25 nails those.

**Why RRF instead of weighted score fusion?**
Reciprocal Rank Fusion is a rank-aggregation method — it doesn't need the
two retrievers' scores to be calibrated to the same scale. That's the
operational pain with weighted score fusion (BM25 scores are unbounded;
cosine similarity is in [-1, 1]).

RRF formula:
```
rrf(d) = Σ_r 1 / (k + rank_r(d))
```
We use `k=60` (the value from the original Cormack et al. SIGIR 2009 paper).

**Trade-off**: two retrievers means two indexes and more memory. For our
demo-scale corpora this is negligible. At 10M+ chunks, you'd consolidate
into a single dense index + keyword filter or move to a hybrid-native engine
like Weaviate or Qdrant.

### 2. Cross-encoder re-ranker on top of hybrid

**Why not skip re-ranking?**
Bi-encoders (BGE-M3) embed query and document independently — fast, but
they don't capture fine-grained query↔document interaction.

Cross-encoders (BGE-reranker-base) jointly encode the pair and output a
relevance score. They're ~10x more accurate on the top of the ranking, but
~100x slower — so we only apply them to the top-20 from hybrid, output
top-5.

Published BGE reranker papers report large nDCG gains on public IR
benchmarks. **This repo does not claim a +20–30% nDCG lift** on the demo
corpus. Local ablation on 20 Q&A showed Hit@1 dropping with rerank and
~50× latency on CPU. Default: `ENABLE_RERANK=false`.

**Trade-off**: rerank is opt-in; enable only when the corpus and latency
budget justify loading the cross-encoder.

### 3. Sliding window 512/64

**Why 512 tokens?**
- Long enough to capture a self-contained concept (a paragraph, a config block)
- Short enough to keep embedding cost low (BGE-M3 has 8K context but most
  useful signal is in the first 512 tokens)
- Aligned with the chunk size most RAG tutorials use, so when comparing
  numbers to public benchmarks we're apples-to-apples

**Why 64 tokens overlap (~12.5%)?**
- High enough that no semantic boundary falls in a dead zone between chunks
- Low enough that we don't 8x our index for marginal recall gain

**Alternatives considered**:
- **Sentence-based splitting** (NLTK, spacy) — but our docs mix Spanish and
  English and have lots of code blocks, which mess up sentence detection.
- **Semantic chunking** (split when embedding similarity drops) — too slow at
  ingest for this demo corpus, and not noticeably better in practice.

### 4. BGE-M3 (multilingual, long-context)

**Why BGE-M3 over OpenAI `text-embedding-3-small`?**
- Runs locally → no per-query cost, no API latency
- Multilingual (100+ languages, strong on Spanish) — important for our use case
- Long context (8K tokens) → can re-embed a chunk without truncation

**Trade-off**: ~400MB to download, ~1GB RAM to run, ~50ms per chunk on CPU.
For 300 documents × 5 chunks each = 1500 chunks, ingest is ~1.5 minutes.

### 5. Gemini 2.0 Flash for generation

**Why not GPT-4o / Claude?**
- Free tier (1,500 req/day) is enough for evaluation runs and demos
- Fast (~1s for 500-token answers)
- Good enough on technical Q&A (not state-of-the-art, but >90% of GPT-4o on
  our eval set)

**Why structured prompting?**
- Force the model to cite chunks with `[#N]` so we can map citations back to
  retrieved sources
- Explicit "I don't know" path when the context doesn't contain the answer
  (avoids hallucination)
- Low temperature (0.2) for grounded, deterministic answers

### 6. Chroma (dev) and Databricks Vector Search (optional)

**Why Chroma for the MVP?**
- Zero ops, runs in-process, persists to disk
- Thin `VectorStore` interface shared with the Databricks adapter
- Lets us focus on the pipeline, not infrastructure

**Current path:** `VECTOR_STORE_BACKEND=chroma` (default) or `databricks`.
There is **no pgvector backend** in this repo.

**When Databricks is useful**:
- Demo against Unity Catalog / Vector Search
- Need for a remote index instead of local Chroma files

## What's intentionally NOT here (yet)

- **Streaming responses**: Gemini supports it; we return the full answer.
  Easy add with `model.generate_content(..., stream=True)`.
- **Conversational memory**: each query is independent. Multi-turn needs a
  query reformulation step + history-aware retriever.
- **Caching of common queries**: a Redis layer in front of `/query` would
  cut latency to ~10ms for hot queries.
- **A/B testing of prompts**: the prompt is in `generator.py`.
- **Langfuse / distributed tracing**: not implemented. `QueryResponse.trace_id`
  is always `None`.
- **Full RAGAS**: not supported; use `scripts/evaluate_light.py`.

## Component dependency graph

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

Every core module is independently importable and unit-testable. The pipeline
accepts constructor injection of any dependency, so tests can swap fakes.
