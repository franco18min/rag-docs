# 📊 Evaluation Guide

This project uses [RAGAS](https://docs.ragas.io/) to measure retrieval and
generation quality. Evaluation is what separates a tutorial RAG from a
production RAG.

## The four metrics

### 1. Faithfulness (target: > 0.85)

**Question**: Is the answer faithful to the retrieved context, or is the model
hallucinating?

**How RAGAS computes it**: Decomposes the answer into atomic claims, then
checks each claim against the context. The score is the fraction of claims
supported by the context.

**What low faithfulness means**:
- Prompt is too permissive (model is making things up)
- Re-ranking is putting low-quality chunks in the context
- Chunk boundaries split important context in half

**Fixes**:
- Lower temperature in the generator
- Add explicit "answer ONLY from context" instructions
- Tighten the re-ranker threshold
- Increase overlap in the chunker

### 2. Context Precision (target: > 0.75)

**Question**: Are the chunks we retrieved actually relevant to the question?

**How RAGAS computes it**: For each retrieved chunk, ask an LLM "is this
chunk useful for answering the question?" then compute precision@k.

**What low context precision means**:
- Embedding model isn't capturing the right similarity (wrong domain model)
- Top-k is too high (irrelevant chunks crowd out relevant ones)
- Hybrid search fusion is overweighting the wrong retriever

**Fixes**:
- Re-tune the RRF `k` constant
- Lower `top_k_vector` / `top_k_bm25` to keep only strong candidates
- Add metadata filtering to narrow the search space

### 3. Context Recall (target: > 0.80)

**Question**: Did we retrieve all the information needed to answer the
question?

**How RAGAS computes it**: Decompose the ground truth answer into claims,
then check if each claim is supported by some retrieved chunk.

**What low context recall means**:
- Chunking is breaking important context across chunk boundaries
- BM25 tokenization is missing important terms
- Embedding model is collapsing semantically different chunks together
- Top-k is too low

**Fixes**:
- Increase chunk overlap
- Increase top-k vector / top-k bm25
- Try a different embedding model
- Add metadata filters (e.g., only docs from the right domain)

### 4. Answer Relevancy (target: > 0.85)

**Question**: Is the answer actually addressing the question asked?

**How RAGAS computes it**: Generate N synthetic questions from the answer
and measure cosine similarity to the original question.

**What low answer relevancy means**:
- Model is being too verbose / going off-topic
- Prompt is too generic
- Re-ranking is bringing in off-topic context

**Fixes**:
- Add "be concise and stay on topic" to the prompt
- Tighten the system prompt
- Use a stronger re-ranker

## Reading the numbers together

| Faithfulness | Context Precision | Context Recall | Answer Relevancy | Diagnosis |
|---|---|---|---|---|
| Low | High | High | Low | Generation problem (prompt or model) |
| High | Low | High | High | Re-ranking problem (top-k too high) |
| High | High | Low | High | Chunking problem (splitting context) |
| Low | Low | Low | Low | Fundamental: wrong corpus, wrong model, or wrong chunking strategy |

## How to run an evaluation

```bash
# 1. Generate a Q&A set (uses Gemini to propose Q&A from your chunks)
python -m scripts.generate_eval_set --collection spark_docs --output data/eval/qa_set.json

# Or use a hand-curated template
cp data/eval/qa_set_template.json data/eval/qa_set.json
# (edit it with your own Q&A)

# 2. Run evaluation
python -m scripts.evaluate \
  --collection spark_docs \
  --eval-set data/eval/qa_set.json \
  --output data/eval/results.json

# 3. Read the results
cat data/eval/results.json
```

## Building a good Q&A set

The quality ceiling of your metrics is the quality of your Q&A set. Tips:

- **30+ questions minimum** for stable metrics
- Mix difficulty: 5 trivial, 15 medium, 10 hard
- Mix types: definitional, procedural, comparative, troubleshooting
- **Ground truth must be 100% in the corpus** — if the answer isn't in the
  indexed docs, context recall will be unfairly low
- **Avoid opinions** — "what's the best framework" is a bad eval question

## When to re-run

- After changing the chunking strategy
- After changing the embedding model
- After changing the re-ranker
- After changing the prompt
- After migrating to a new vector DB

Always diff the metrics against the previous baseline. If a change makes
some metrics better and others worse, the trade-off is a product decision,
not an engineering one.
