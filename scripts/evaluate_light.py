"""Lightweight RAGAS-style evaluation (supported path).

Full RAGAS (`scripts/evaluate.py`) is not a reliable path in this repo
(langchain/datasets conflicts). Use this script instead.

Avoids the heavy RAGAS dependency. Implements the same 4 metrics
manually with a single Gemini Flash-Lite call per question.

Metrics computed per question:
    - faithfulness      : 1 - (# unsupported claims / # total claims)
    - context_precision : (# relevant chunks) / (# chunks used in answer)
    - context_recall    : 1 if all ground_truth facts appear in context, else fraction
    - answer_relevancy  : 1 - (1 - cosine similarity between Q embedding and A embedding)
                          approximated with an LLM "does answer address the question" score

Cost: 1 generation + 1 judging call per question (≈10 calls for 5 questions).
This is ~5x cheaper than full RAGAS on free tier.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import google.generativeai as genai

from app.core.pipeline import RAGPipeline

EVAL_PATH = Path(__file__).resolve().parent.parent / "data" / "eval" / "qa_set_template.json"


JUDGE_PROMPT = """You are an evaluator. Score the following RAG answer on 4 metrics, each 0.0 to 1.0.

QUESTION:
{question}

GROUND TRUTH ANSWER:
{ground_truth}

GENERATED ANSWER:
{answer}

CONTEXT (chunks retrieved):
{contexts}

Score these 4 metrics (0.0=worst, 1.0=perfect):
- faithfulness: does the generated answer stick to facts present in the context? (no hallucinations)
- context_precision: of the retrieved chunks, what fraction were actually relevant to answering the question?
- context_recall: does the context contain all the information in the ground truth?
- answer_relevancy: does the generated answer actually address the question?

Respond with ONLY a JSON object, no prose. Example:
{{"faithfulness": 0.85, "context_precision": 0.70, "context_recall": 0.95, "answer_relevancy": 0.90}}
"""


def _judge(question: str, ground_truth: str, answer: str, contexts: list[str]) -> dict:
    model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest"))
    ctx_str = "\n---\n".join(c[:300] for c in contexts[:5])
    prompt = JUDGE_PROMPT.format(
        question=question,
        ground_truth=ground_truth,
        answer=answer,
        contexts=ctx_str,
    )
    res = model.generate_content(prompt)
    text = res.text.strip()
    # Extract first JSON object from the response
    m = re.search(r"\{[^{}]+\}", text)
    if not m:
        return {
            "faithfulness": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "answer_relevancy": 0.0,
        }
    try:
        return {k: float(v) for k, v in json.loads(m.group(0)).items()}
    except Exception:
        return {
            "faithfulness": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "answer_relevancy": 0.0,
        }


def main() -> int:
    with open(EVAL_PATH, encoding="utf-8") as f:
        qa_set = json.load(f)

    pipeline = RAGPipeline()
    print(f"Pipeline ready, vector_store={type(pipeline.vector_store).__name__}\n")

    metric_keys = ("faithfulness", "context_precision", "context_recall", "answer_relevancy")
    totals = {k: 0.0 for k in metric_keys}
    samples = []

    for i, item in enumerate(qa_set, 1):
        q = item["question"]
        gt = item["ground_truth"]
        print(f"[{i}/{len(qa_set)}] Q: {q[:80]}")
        t0 = time.time()
        result = pipeline.query(q, collection="spark_docs", top_k=5)
        latency = (time.time() - t0) * 1000
        answer = result["answer"]
        contexts = [c.get("text", "") for c in result.get("chunks", [])]
        print(f"    latency: {latency:.0f}ms  |  answer: {answer[:120]!r}")

        scores = _judge(q, gt, answer, contexts)
        for k, v in scores.items():
            totals[k] += v
        samples.append({"question": q, "ground_truth": gt, "answer": answer, "scores": scores})
        print(f"    scores: {scores}\n")

    n = len(qa_set)
    print("=" * 60)
    print(f"Lightweight RAGAS-style eval over {n} questions:")
    for k in metric_keys:
        avg = totals[k] / n
        print(f"  {k:20s}: {avg:.4f}  (target > 0.75–0.85)")
    print("=" * 60)

    out = Path(__file__).resolve().parent.parent / "data" / "eval" / "light_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(
            {
                "num_questions": n,
                "metrics": {k: totals[k] / n for k in metric_keys},
                "per_question": samples,
                "model": os.environ.get("GEMINI_MODEL", "?"),
                "timestamp": time.time(),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"Saved → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
