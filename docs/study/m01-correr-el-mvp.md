# Módulo 1 — Correr el MVP y mirar un request

**Tiempo:** 45–90 min (la primera vez incluye install). **Prerrequisito:** módulo 0.

```
Estoy en el módulo 1 (docs/study/m01-correr-el-mvp.md).
Guiame. Ya entendí RAG vs fine-tuning. No saltees a chunking.
En cada parada esperá lo que observé en el JSON.
```

---

## Hoy te quiero dejar haciendo esto

Un loop cerrado: **ingerir** `data/sample/` → **preguntar** por HTTP →
leer `answer` y `citations` como un data engineer lee un row de salida.

---

## Paso 1 — Qué vas a levantar

Tres procesos mentales, dos procesos de máquina:

| Pieza | Rol |
|---|---|
| Ingest (`scripts/ingest.py`) | Batch: docs → chunks → Chroma + BM25 |
| API (`uvicorn app.main:app`) | Servicio `/query` |
| Streamlit (opcional) | UI sobre la misma API |

Gemini necesita `GOOGLE_API_KEY` (free tier). Los embeddings son
locales: la primera corrida descarga BGE-M3 (~cientos de MB).

Seguí el README (“Arranque rápido”). Si algo falla, pegame el error
**completo** en el chat: eso es parte de la clase, no un desvío.

---

## Paso 2 — El contrato de salida

Abrí `app/models/response.py` y mirá `QueryResponse` y `Citation`.

Campos que te importan hoy:

- `answer` — texto del LLM.
- `citations` — de qué archivo salió cada fragmento, snippet, `score`.
- `latency_ms` — presupuesto de producto, no vanidad.
- `model` — debería ser `gemini-flash-lite-latest`.
- `chunks_retrieved` — cuántos chunks llegaron al generador.
- `trace_id` — **siempre `None`**. Langfuse no está. Si esperabas un
  APM, ese hueco es consciente.

El `score` **no es una probabilidad**. Es un número de ranking /
similitud. No lo uses como “92% de certeza”.

---

## Paso 3 — Dos preguntas, dos mundos

El laboratorio no es “que conteste lindo”. Es **contrastar**.

**Pregunta A (in-corpus).** Algo que está en `data/sample/`, por
ejemplo arquitectura Medallion, time travel de Delta, o BGE-M3.
Deberías ver citas a un `.md` real.

**Pregunta B (fuera de corpus).** Algo que ningún markdown tiene
(“¿cuál es el salario del CEO de Databricks?”). El prompt está
diseñado para que diga que **no encuentra** esa información.

Si B inventa un número, eso es un hallazgo de clase (fallo de
grounding). Anotalo y seguimos en el módulo 6; no “arregles” el
prompt todavía.

---

## Parada 1 — Antes de pegar curl

1. ¿Qué archivo de sample usarías como `expected_source` para una
   pregunta sobre Medallion?
2. Si `trace_id` viene poblado, ¿qué concluirías? (pista: el código
   actual no debería).

Respondeme y recién después corré las dos queries.

---

## Laboratorio 1

1. Ingest con rebuild si es la primera vez (`README`).
2. `POST /query` con la pregunta A. Guardá (o copiá) `citations[].source`
   y `chunks_retrieved`.
3. Lo mismo con la pregunta B.
4. Opcional: Streamlit en `:8501` y repetí A/B. Misma API, otra piel.

Pegame en el chat un recorte: A (¿citó el md correcto?) y B (¿dijo que
no sabe, o alucinó?).

---

## Criterio para pasar al módulo 2

- [ ] El stack arrancó (o documentaste el blocker y lo destrabamos).
- [ ] Sabés qué significa cada campo de `QueryResponse`.
- [ ] Contrastaste in-corpus vs fuera de corpus.

```
Cierre módulo 1: pregunta A citó [archivo]; pregunta B hizo [X].
Listo para el módulo 2.
```
