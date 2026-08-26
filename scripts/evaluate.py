"""
RAGAS evaluation runner.

Loads a Q&A set with ground truth, runs each question through the RAG
pipeline, and computes RAGAS metrics:
    - faithfulness           (¿la respuesta es fiel al contexto?)
    - context_precision      (¿los chunks retrieved son relevantes?)
    - context_recall         (¿recuperamos toda la info necesaria?)
    - answer_relevancy       (¿la respuesta es relevante a la pregunta?)

Usage:
    python -m scripts.evaluate --collection spark_docs --eval-set data/eval/qa_set.json
    python -m scripts.evaluate --collection spark_docs --eval-set data/eval/qa_set.json --output data/eval/results.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from app.core.pipeline import RAGPipeline

logger = logging.getLogger("evaluate")


def main():
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation on a Q&A set")
    parser.add_argument("--collection", required=True, help="Collection to query")
    parser.add_argument("--eval-set", required=True, help="Path to Q&A JSON file")
    parser.add_argument("--output", default="data/eval/results.json", help="Where to write results")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # --- Load eval set ---
    eval_path = Path(args.eval_set)
    if not eval_path.exists():
        print(f"❌ Eval set not found: {eval_path}")
        print("   Generá uno con: python -m scripts.generate_eval_set --collection <name>")
        sys.exit(1)
    with open(eval_path, encoding="utf-8") as f:
        qa_pairs = json.load(f)
    print(f"📋 {len(qa_pairs)} Q&A pairs loaded from {eval_path}")

    if not qa_pairs:
        print("❌ Eval set is empty.")
        sys.exit(1)

    # --- Init pipeline ---
    print("🚀 Initializing pipeline (loads BGE-M3 + reranker, may take ~30s)...")
    pipeline = RAGPipeline()

    # --- Run pipeline on each question ---
    print(f"🔎 Running {len(qa_pairs)} queries against collection '{args.collection}'...")
    samples: list[dict] = []
    for i, qa in enumerate(qa_pairs, start=1):
        question = qa["question"]
        ground_truth = qa["ground_truth"]
        try:
            result = pipeline.query(
                question=question,
                collection=args.collection,
                top_k=args.top_k,
            )
        except Exception as e:
            logger.warning("Query %d failed: %s", i, e)
            continue

        contexts = [c.get("text", "") for c in result.get("chunks", [])]
        samples.append(
            {
                "question": question,
                "answer": result["answer"],
                "contexts": contexts,
                "ground_truth": ground_truth,
            }
        )
        if i % 5 == 0:
            print(f"   ... {i}/{len(qa_pairs)} done")

    if not samples:
        print("❌ No queries succeeded.")
        sys.exit(1)

    print(f"✅ {len(samples)} queries completed. Computing RAGAS metrics...")

    # --- RAGAS ---
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
    except ImportError as e:
        print(f"❌ RAGAS not installed: {e}")
        print("   pip install ragas==0.1.5 datasets==2.16.1")
        sys.exit(1)

    dataset = Dataset.from_list(samples)

    try:
        scores = evaluate(
            dataset,
            metrics=[faithfulness, context_precision, context_recall, answer_relevancy],
        )
    except Exception as e:
        logger.exception("RAGAS evaluation failed")
        print(f"❌ RAGAS failed: {e}")
        sys.exit(1)

    # --- Print & save ---
    df = scores.to_pandas()
    print("\n" + "=" * 60)
    print("📊 RAGAS Evaluation Results")
    print("=" * 60)
    metric_cols = [c for c in df.columns if c in ("faithfulness", "context_precision", "context_recall", "answer_relevancy")]
    for col in metric_cols:
        mean = df[col].mean()
        print(f"   {col:25s}: {mean:.4f}  (target > 0.75–0.85)")
    print("=" * 60)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "collection": args.collection,
                "num_questions": len(samples),
                "metrics": {col: float(df[col].mean()) for col in metric_cols},
                "per_question": df.to_dict(orient="records"),
                "timestamp": time.time(),
            },
            f,
            indent=2,
            default=str,
        )
    print(f"💾 Detailed results saved to {output_path}")


if __name__ == "__main__":
    main()
