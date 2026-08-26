"""
Generate a Q&A evaluation set.

Two modes:
    1. From a collection (recommended): use Gemini to generate Q&A pairs
       grounded in the actual chunks. Produces high-quality, context-faithful
       ground truth.
    2. From a JSON template: load an existing eval set (hand-curated).

Usage:
    # Auto-generate from a collection (requires GOOGLE_API_KEY)
    python -m scripts.generate_eval_set --collection spark_docs --output data/eval/qa_set.json --num-questions 30

    # From a hand-curated JSON
    python -m scripts.generate_eval_set --from-template data/eval/qa_set_template.json --output data/eval/qa_set.json
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

from app.config import settings
from app.core.pipeline import RAGPipeline


logger = logging.getLogger("generate_eval_set")


GENERATION_PROMPT = """Sos un experto en crear datasets de evaluación para sistemas RAG.

Te voy a dar un fragmento de documentación técnica. Tu tarea es generar UNA pregunta
cuya respuesta esté EXPLÍCITAMENTE en el fragmento, junto con la respuesta ground truth.

Reglas:
1. La pregunta debe ser específica y técnica (no genérica).
2. La respuesta ground truth debe ser tomada TEXTUALMENTE del fragmento, o una
   paráfrasis muy cercana. NO inventes información.
3. La respuesta debe ser concisa (2-4 oraciones) y completa.
4. Variá el tipo de pregunta: definicional ("qué es X"), procedural ("cómo
   hacer Y"), comparativa ("diferencia entre A y B"), troubleshooting
   ("por qué falla Z").
5. Respondé SOLO con un JSON válido con esta estructura:
   {{"question": "...", "ground_truth": "...", "context_relevance": "high|medium|low"}}

Fragmento:
---
{chunk}
---

JSON:"""


def generate_from_collection(
    pipeline: RAGPipeline,
    collection: str,
    num_questions: int,
    output_path: Path,
    min_chunk_chars: int = 300,
    max_chunk_chars: int = 2500,
) -> int:
    """Sample chunks from a collection and ask Gemini to generate Q&A pairs."""
    import google.generativeai as genai

    if not settings.google_api_key:
        print("❌ GOOGLE_API_KEY no configurada. No puedo generar Q&A automáticamente.")
        print("   Opciones:")
        print("   1. Configurá la key en .env y reintentá")
        print("   2. Editá el template data/eval/qa_set_template.json a mano y usá --from-template")
        sys.exit(1)

    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    # Sample chunks from the collection
    vector_store = pipeline.vector_store
    coll = vector_store.get_or_create_collection(collection)
    total = coll.count()
    if total == 0:
        print(f"❌ La colección '{collection}' está vacía. Ingestá documentos primero.")
        sys.exit(1)

    print(f"📊 Colección '{collection}': {total} chunks")

    # Get a sample of chunks via random offsets
    sample_size = min(num_questions * 2, total)
    rng = random.Random(42)
    offsets = rng.sample(range(total), k=sample_size)

    qa_pairs: list[dict] = []
    seen_questions: set[str] = set()
    fetched = coll.get(limit=sample_size, include=["documents", "metadatas"])
    chunks_text = fetched.get("documents", [])

    for chunk in chunks_text:
        if not chunk or len(chunk) < min_chunk_chars or len(chunk) > max_chunk_chars:
            continue
        try:
            response = model.generate_content(
                GENERATION_PROMPT.format(chunk=chunk[:3000]),
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=512,
                ),
            )
            text = response.text.strip()
            # Extract JSON (Gemini sometimes wraps it in ```json ... ```)
            if text.startswith("```"):
                text = text.split("```", 2)[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)
        except Exception as e:
            logger.warning("Failed to generate Q&A for a chunk: %s", e)
            continue

        q = data.get("question", "").strip()
        gt = data.get("ground_truth", "").strip()
        if not q or not gt or q in seen_questions:
            continue
        seen_questions.add(q)
        qa_pairs.append(
            {
                "question": q,
                "ground_truth": gt,
                "context_relevance": data.get("context_relevance", "medium"),
            }
        )
        if len(qa_pairs) >= num_questions:
            break

    if not qa_pairs:
        print("❌ No se pudieron generar Q&A. ¿Tenés API key válida?")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, indent=2, ensure_ascii=False)

    print(f"✅ {len(qa_pairs)} Q&A pairs escritos en {output_path}")
    return len(qa_pairs)


def from_template(template_path: Path, output_path: Path) -> int:
    """Copy/normalize a hand-curated eval set."""
    if not template_path.exists():
        print(f"❌ Template no encontrado: {template_path}")
        sys.exit(1)
    with open(template_path, "r", encoding="utf-8") as f:
        qa = json.load(f)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(qa, f, indent=2, ensure_ascii=False)
    print(f"✅ {len(qa)} Q&A pairs copiados de {template_path} a {output_path}")
    return len(qa)


def main():
    parser = argparse.ArgumentParser(description="Generate a Q&A evaluation set")
    parser.add_argument("--collection", help="Collection to sample chunks from")
    parser.add_argument("--num-questions", type=int, default=30)
    parser.add_argument("--output", default="data/eval/qa_set.json")
    parser.add_argument("--from-template", help="Use a hand-curated JSON template instead")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    output = Path(args.output)

    if args.from_template:
        from_template(Path(args.from_template), output)
    elif args.collection:
        pipeline = RAGPipeline()
        generate_from_collection(
            pipeline=pipeline,
            collection=args.collection,
            num_questions=args.num_questions,
            output_path=output,
        )
    else:
        parser.error("Especificá --collection o --from-template")


if __name__ == "__main__":
    main()
