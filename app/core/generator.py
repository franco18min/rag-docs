"""
Gemini generation wrapper.

Generates an answer from a query + context chunks, with explicit citation
formatting. Uses structured prompting to force the model to ground every
claim in the provided context.
"""
from __future__ import annotations

import logging
import re

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)

# 1-based citation markers as they appear in the model answer, e.g. [#2].
_CITATION_RE = re.compile(r"\[#(\d+)\]")

SYSTEM_INSTRUCTION = """Sos un asistente técnico que responde preguntas sobre documentación técnica.
Reglas estrictas:
1. Respondé SOLO basándote en el contexto proporcionado. Si la respuesta no está en el contexto, decí "No encuentro esa información en los documentos indexados" y sugerí reformular la pregunta.
2. Incluí citas numéricas [#1], [#2], etc. que referencien a los chunks provistos.
3. Sé conciso y técnico. Usá listas o tablas cuando ayude a la claridad.
4. No inventes comandos, flags, versiones, ni URLs. Si dudás, decí que no estás seguro.
5. Respondé en el mismo idioma de la pregunta.
"""


USER_PROMPT_TEMPLATE = """Pregunta: {question}

Contexto recuperado (cada chunk tiene un número de cita):
{context}

Respondé la pregunta usando EXCLUSIVAMENTE el contexto de arriba. Citá los chunks relevantes con el formato [#N] donde N es el número del chunk.
"""


class Generator:
    """Google Gemini wrapper with structured prompting for grounded answers."""

    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        self.model_name = model_name or settings.gemini_model
        self.api_key = api_key or settings.google_api_key
        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY no está configurada. "
                "Obtené una gratis en https://aistudio.google.com/app/apikey y ponela en .env"
            )
        genai.configure(api_key=self.api_key)

        # Safety settings: allow technical content (code, configs) but block
        # the obviously dangerous categories.
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ]

        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=SYSTEM_INSTRUCTION,
            safety_settings=self.safety_settings,
        )

    def generate(self, question: str, context_chunks: list[dict]) -> str:
        """Generate an answer given a question and retrieved context chunks.

        Args:
            question: The user's question.
            context_chunks: List of dicts with keys ``text`` and ``metadata``
                (the top-k chunks after re-ranking).

        Returns:
            The generated answer text.
        """
        if not context_chunks:
            return (
                "No encontré información relevante en los documentos indexados. "
                "Probá reformulando la pregunta o verificá que la colección correcta esté cargada."
            )

        context = self._format_context(context_chunks)
        prompt = USER_PROMPT_TEMPLATE.format(question=question, context=context)

        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,  # low temperature for grounded answers
                top_p=0.9,
                top_k=40,
                max_output_tokens=1024,
            ),
        )

        return response.text

    @staticmethod
    def _format_context(chunks: list[dict]) -> str:
        """Format chunks as numbered context blocks ``[#N] [Fuente: ...]``."""
        parts: list[str] = []
        for i, c in enumerate(chunks, start=1):
            md = c.get("metadata", {}) or {}
            source = md.get("source", "unknown")
            section = md.get("section") or ""
            header = f"[#{i}] [Fuente: {source}"
            if section:
                header += f" — Sección: {section}"
            header += "]"
            parts.append(f"{header}\n{c.get('text', '').strip()}\n")
        return "\n".join(parts)


def _chunk_to_citation(chunk: dict, citation_number: int) -> dict:
    """Map a retrieved chunk dict to a Citation-compatible payload."""
    md = chunk.get("metadata") or {}
    text = (chunk.get("text") or "").strip()
    snippet = text[:500]
    score = chunk.get("score", md.get("score", 0.0))
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0
    page = md.get("page")
    if page is not None:
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = None
    chunk_index = md.get("chunk_index")
    if chunk_index is not None:
        try:
            chunk_index = int(chunk_index)
        except (TypeError, ValueError):
            chunk_index = None
    return {
        "source": md.get("source") or "unknown",
        "section": md.get("section"),
        "page": page,
        "chunk_index": chunk_index,
        "text_snippet": snippet,
        "score": score,
        "citation_number": citation_number,
    }


def parse_citations(answer: str, context_chunks: list[dict]) -> list[dict]:
    """Select citations from ``[#N]`` markers in ``answer``.

    ``N`` is 1-based and indexes ``context_chunks`` in the same order used by
    ``Generator._format_context``. Markers are kept in **order of first
    appearance** in the answer; duplicate ``N`` values are ignored. Out-of-range
    ``N`` is skipped.

    If no valid markers are found, returns the full top-k list (one citation
    per chunk, numbered 1..k) and logs a warning.
    """
    seen: set[int] = set()
    numbers: list[int] = []
    for match in _CITATION_RE.finditer(answer or ""):
        n = int(match.group(1))
        if n in seen:
            continue
        if 1 <= n <= len(context_chunks):
            seen.add(n)
            numbers.append(n)

    if not numbers:
        logger.warning(
            "No parseable [#N] citations in the generated answer; "
            "falling back to top-k context chunks"
        )
        return [
            _chunk_to_citation(chunk, i)
            for i, chunk in enumerate(context_chunks, start=1)
        ]

    return [_chunk_to_citation(context_chunks[n - 1], n) for n in numbers]
