"""
Gemini generation wrapper.

Generates an answer from a query + context chunks, with explicit citation
formatting. Uses structured prompting to force the model to ground every
claim in the provided context.
"""
from __future__ import annotations

import os
from typing import Optional

import google.generativeai as genai

from app.config import settings


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

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
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
        """Format chunks as numbered context blocks."""
        parts: list[str] = []
        for i, c in enumerate(chunks, start=1):
            md = c.get("metadata", {}) or {}
            source = md.get("source", "unknown")
            section = md.get("section") or ""
            header = f"[Fuente: {source}"
            if section:
                header += f" — Sección: {section}"
            header += "]"
            parts.append(f"{header}\n{c.get('text', '').strip()}\n")
        return "\n".join(parts)
