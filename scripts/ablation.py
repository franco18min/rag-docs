"""Ablation: compare vector-only vs hybrid (vector+BM25) vs hybrid+rerank.

Runs each question in the eval set through 3 retrieval configurations and
measures Hit@K (does the expected source file appear in top-K) and mean
reciprocal rank (MRR) for each. Saves results to data/eval/ablation.json.

On a small corpus, vector and hybrid often score similarly; this script
reports Hit@K / MRR from labeled expected_source, not a narrative winner.

Usage:
    python scripts/ablation.py --eval-set data/eval/qa_set.json
    python scripts/ablation.py --eval-set data/eval/qa_set.json --top-k 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Force Chroma for the ablation (no need to bring up Databricks just to
# compare retrieval strategies).
os.environ["VECTOR_STORE_BACKEND"] = "chroma"

from app.config import settings  # noqa: E402
from app.core.bm25_store import BM25Store  # noqa: E402
from app.core.embedder import Embedder  # noqa: E402
from app.core.hybrid_search import HybridSearch  # noqa: E402
from app.core.reranker import Reranker  # noqa: E402
from app.core.vector_store import VectorStore  # noqa: E402


def _normalize_source(raw: str) -> str:
    """Best-effort: take the trailing filename out of a path that may have
    had its separators mangled by SQL escaping."""
    for sep in ("/", "\\"):
        if sep in raw:
            raw = raw.rsplit(sep, 1)[-1]
    return raw


def evaluate_config(
    name: str,
    *,
    embedder: Embedder,
    vector_store: VectorStore,
    bm25_store: BM25Store,
    reranker: Reranker,
    qa_set: list[dict],
    top_k: int,
    use_hybrid: bool,
    use_rerank: bool,
) -> dict:
    """Run one retrieval configuration against the full eval set and return metrics."""
    hits = {1: 0, 3: 0, 5: 0}
    reciprocal_ranks = []
    latencies = []
    detail = []

    hybrid = HybridSearch(vector_store, bm25_store)

    for item in qa_set:
        q = item["question"]
        expected = (item.get("expected_source") or "").strip()
        if not expected:
            detail.append({"question": q, "expected": "", "top5": [], "skipped": True})
            continue

        t0 = time.time()
        q_emb = embedder.embed_query(q).tolist()
        if use_hybrid:
            candidates = hybrid.search(
                collection=settings.collection_name,
                query=q,
                query_embedding=q_emb,
                top_k_vector=settings.top_k_vector,
                top_k_bm25=settings.top_k_bm25,
            )
        else:
            candidates = vector_store.query(
                collection=settings.collection_name,
                query_embedding=q_emb,
                top_k=max(top_k * 4, settings.top_k_vector),
            )
        if use_rerank:
            results = reranker.rerank(q, candidates, top_k=top_k)
        else:
            results = candidates[:top_k]
        latencies.append((time.time() - t0) * 1000)

        sources = [_normalize_source(r.get("metadata", {}).get("source", "")) for r in results]

        def _matches(src: str, expected_source: str = expected) -> bool:
            exp = _normalize_source(expected_source)
            s = _normalize_source(src)
            return exp in s or s in exp or Path(exp).stem == Path(s).stem

        for k in (1, 3, 5):
            if any(_matches(s) for s in sources[:k]):
                hits[k] += 1
        try:
            rank = next(i + 1 for i, s in enumerate(sources) if _matches(s))
            reciprocal_ranks.append(1.0 / rank)
        except StopIteration:
            reciprocal_ranks.append(0.0)

        detail.append({"question": q, "expected": expected, "top5": sources})

    n = len(reciprocal_ranks) or 1
    return {
        "config": name,
        "num_questions": len(reciprocal_ranks),
        "hit_at_1": hits[1] / n,
        "hit_at_3": hits[3] / n,
        "hit_at_5": hits[5] / n,
        "mrr": sum(reciprocal_ranks) / n,
        "avg_latency_ms": (sum(latencies) / len(latencies)) if latencies else 0.0,
        "detail": detail,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--eval-set", default="data/eval/qa_set.json")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--output", default="data/eval/ablation.json")
    p.add_argument("--collection", default=settings.collection_name)
    args = p.parse_args()

    # Verify the collection has data. If not, abort and tell the user.
    vs = VectorStore()
    count = vs.collection_count(args.collection)
    if count == 0:
        print(f"Collection '{args.collection}' is empty.")
        print(
            "Run first: python -m scripts.ingest --source data/raw --collection spark_docs --rebuild"
        )
        return 1

    with open(args.eval_set, encoding="utf-8") as f:
        qa_set = json.load(f)
    print(
        f"Ablation over {len(qa_set)} questions, top_k={args.top_k}, collection={args.collection}"
    )
    print(f"Collection has {count} chunks\n")

    embedder = Embedder()
    reranker = Reranker()

    configs = [
        ("vector-only", dict(use_hybrid=False, use_rerank=False)),
        ("hybrid (BM25+vector, RRF)", dict(use_hybrid=True, use_rerank=False)),
        ("hybrid + rerank (full stack)", dict(use_hybrid=True, use_rerank=True)),
    ]

    # BM25 is needed for the hybrid configurations. The VectorStore
    # doesn't own the BM25 index directly — it's a separate BM25Store that
    # persists to a pickle on disk. We build a HybridSearch with the same
    # vector store and the BM25 store sharing the same collection name.
    bm25_store = BM25Store()

    results = []
    for name, kwargs in configs:
        print(f"  Running: {name} ...")
        r = evaluate_config(
            name,
            embedder=embedder,
            vector_store=vs,
            bm25_store=bm25_store,
            reranker=reranker,
            qa_set=qa_set,
            top_k=args.top_k,
            **kwargs,
        )
        results.append(r)
        print(
            f"    Hit@1={r['hit_at_1']:.3f}  Hit@3={r['hit_at_3']:.3f}  "
            f"Hit@5={r['hit_at_5']:.3f}  MRR={r['mrr']:.3f}  "
            f"avg={r['avg_latency_ms']:.0f}ms"
        )

    # Print summary table
    print("\n" + "=" * 72)
    print(
        f"{'Configuration':<40s} {'Hit@1':>7s} {'Hit@3':>7s} {'Hit@5':>7s} {'MRR':>7s} {'ms':>7s}"
    )
    print("-" * 72)
    for r in results:
        print(
            f"{r['config']:<40s} {r['hit_at_1']:>7.3f} {r['hit_at_3']:>7.3f} "
            f"{r['hit_at_5']:>7.3f} {r['mrr']:>7.3f} {r['avg_latency_ms']:>7.0f}"
        )
    print("=" * 72)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"eval_set": args.eval_set, "top_k": args.top_k, "results": results},
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\nSaved → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
