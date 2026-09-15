"""
Streamlit UI for the RAG Docs demo.

Run with:
    streamlit run app/streamlit_app.py

The UI talks to the FastAPI backend at the URL configured in `api_url`
(default: http://localhost:8000). The backend must be running.
"""

from __future__ import annotations

import os

import requests
import streamlit as st

from app.config import settings

API_URL = os.getenv("RAG_API_URL", "http://localhost:8000")
DEFAULT_COLLECTION = settings.collection_name


def api_get(path: str) -> dict:
    r = requests.get(f"{API_URL}{path}", timeout=30)
    r.raise_for_status()
    return r.json()


def api_post(path: str, payload: dict) -> dict:
    r = requests.post(f"{API_URL}{path}", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def main():
    st.set_page_config(
        page_title="RAG Docs",
        page_icon=None,
        layout="wide",
    )

    st.title("RAG Docs")
    st.caption(
        "Sistema de preguntas y respuestas sobre documentación técnica · "
        "Búsqueda híbrida (BM25 + vector) con re-ranking cross-encoder y Gemini Flash-Lite"
    )

    # ---- Sidebar ----
    with st.sidebar:
        st.header("Configuración")
        try:
            health = api_get("/health")
            st.success(f"API OK · {health.get('model', '?')}")
            st.caption(f"Embeddings: {health.get('embedding_model', '?')}")
            st.caption(f"Re-ranker: {health.get('reranker_model', '?')}")
            collections = api_get("/collections").get("collections", [])
        except Exception as e:
            st.error(f"No se pudo conectar a la API en {API_URL}\n\n{e}")
            st.stop()

        if not collections:
            st.warning(
                "No hay colecciones. Corré `python -m scripts.ingest --source ./data/raw --collection <name>` primero."
            )
            st.stop()

        collection = st.selectbox("Colección", collections, index=0)
        top_k = st.slider("Top K (chunks para respuesta)", 1, 10, 5)
        show_chunks = st.checkbox("Mostrar chunks recuperados", value=True)
        st.divider()
        st.caption(f"API: `{API_URL}`")

    # ---- Main ----
    example_questions = [
        "¿Cómo funciona la arquitectura Medallion en Databricks?",
        "¿Qué es Delta Lake y en qué se diferencia de Parquet?",
        "¿Cómo configuro un job de Spark con auto-scaling?",
        "¿Cuándo usar structured streaming vs batch?",
        "Explicame la diferencia entre cache y persist en Spark.",
    ]
    st.subheader("Hacé una pregunta")
    col_q, col_ex = st.columns([3, 1])
    with col_q:
        question = st.text_input(
            "Pregunta",
            placeholder="Escribí tu pregunta y Enter...",
            label_visibility="collapsed",
        )
    with col_ex:
        example = st.selectbox(
            "Ejemplos",
            options=["(elegí)"] + example_questions,
            label_visibility="collapsed",
        )
    if example and example != "(elegí)":
        question = example

    if not question:
        st.info("Escribí una pregunta o elegí un ejemplo para empezar.")
        return

    # ---- Query ----
    with st.spinner("Buscando contexto y generando respuesta..."):
        try:
            response = api_post(
                "/query",
                {
                    "question": question,
                    "collection": collection,
                    "top_k": top_k,
                    "include_citations": True,
                },
            )
        except requests.HTTPError as e:
            st.error(f"Error de la API: {e.response.text}")
            st.stop()
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    # ---- Answer ----
    st.subheader("Respuesta")
    st.markdown(response["answer"])

    # ---- Stats ----
    st.caption(
        f"Latencia: {response['latency_ms']:.0f} ms · "
        f"Chunks: {response['chunks_retrieved']} · "
        f"Modelo: {response['model']} · "
        f"Colección: {response['collection']}"
    )

    # ---- Citations ----
    citations = response.get("citations", [])
    if show_chunks and citations:
        st.subheader("Citas")
        for i, c in enumerate(citations, start=1):
            n = c.get("citation_number") or i
            with st.expander(
                f"#{n} — {c.get('source', '?').split('/')[-1]}  ·  score {c.get('score', 0):.3f}"
            ):
                if c.get("section"):
                    st.caption(f"Sección: {c['section']}")
                st.text(c.get("text_snippet", ""))


if __name__ == "__main__":
    main()
