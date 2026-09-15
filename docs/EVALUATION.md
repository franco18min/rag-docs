# Evaluation Guide

This repo measures retrieval and generation on a **small demo corpus**
(`data/sample/`, 8 markdowns). Numbers in the README are **historical**
for that corpus; they do not imply production quality or that hybrid
“wins” over vector.

**Supported path:** `python scripts/evaluate_light.py` (LLM-as-judge,
one call per question).

**Not supported:** full RAGAS via `scripts/evaluate.py`. That script
prints a disclaimer and often fails on langchain / datasets version
conflicts. Treat failures as expected.

Each Q&A in `data/eval/qa_set.json` includes `expected_source` (markdown
filename). Ablation uses that field; it does not guess the source from
question text.

## The four metrics (light judge)

Targets below are **diagnostic hints**, not résumé claims. Precision and
recall on n≈20 with an LLM judge are **not** achievements.

### 1. Faithfulness

**Question**: Is the answer faithful to the retrieved context, or is the model
hallucinating?

The light judge scores this as a 0–1 from claim support in context (not
the official RAGAS decomposition pipeline).

**What low faithfulness means**:
- Prompt is too permissive (model is making things up)
- Low-quality chunks in the context
- Chunk boundaries split important context in half

**Fixes**:
- Lower temperature in the generator
- Add explicit "answer ONLY from context" instructions
- Increase overlap in the chunker

### 2. Context Precision

**Question**: Are the chunks we retrieved actually relevant to the question?

On this corpus the historical light score is **low (~0.40)**. That is a
strict judge + small n, not a ranking of the retriever.

**What low context precision can mean**:
- Top-k is high (irrelevant chunks in the window)
- Judge marks long/comprehensive answers harshly

### 3. Context Recall

**Question**: Did we retrieve the information needed to answer the
question?

Historical light score **~0.59** on n=20. Same caveat: do not sell it as
a retrieval win or loss.

**What low context recall can mean**:
- Chunking splits facts across boundaries
- Top-k is too low
- Ground truth is more specific than the retrieved snippets

### 4. Answer Relevancy

**Question**: Is the answer actually addressing the question asked?

The light path approximates this with an LLM score (not RAGAS cosine of
synthetic questions).

## Reading the numbers together

| Faithfulness | Context Precision | Context Recall | Answer Relevancy | Diagnosis (heuristic) |
|---|---|---|---|---|
| Low | High | High | Low | Generation problem (prompt or model) |
| High | Low | High | High | Window/top-k or judge strictness |
| High | High | Low | High | Chunking / missing facts |
| Low | Low | Low | Low | Corpus, model, or chunking mismatch |

Ablation Hit@K / MRR on this demo: **hybrid ≈ vector**. Rerank can lower
Hit@1 and add latency. See README tables; do not treat one run as an
architecture ranking.

## How to run (supported)

```bash
# Hand-curated set (preferred; has expected_source)
# data/eval/qa_set.json is already populated for the sample corpus

# Light evaluation (supported)
python scripts/evaluate_light.py

# Retrieval ablation (Hit@K / MRR from expected_source)
python scripts/ablation.py --eval-set data/eval/qa_set.json
```

Optional: generate extra Q&A with Gemini, then add `expected_source`
yourself:

```bash
python -m scripts.generate_eval_set --collection spark_docs --output data/eval/qa_set.json
```

Full RAGAS (unsupported):

```bash
python -m scripts.evaluate \
  --collection spark_docs \
  --eval-set data/eval/qa_set.json \
  --output data/eval/results.json
```

## Building a good Q&A set

- Include **`expected_source`** matching a sample markdown filename
  (`delta_lake_intro.md`, `retrieval.md`, …)
- Ground truth must be answerable from the indexed docs
- Mix definitional / procedural / comparative questions
- n=20 on 8 files is enough to smoke-test, not enough to rank systems

## When to re-run

- After changing chunking, embeddings, retriever, rerank, or prompt
- Diff against the previous baseline on the **same** eval set
- If some metrics rise and others fall, that is a product trade-off
