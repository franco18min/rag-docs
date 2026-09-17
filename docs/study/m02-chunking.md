# Módulo 2 — Ingestión: loaders, chunks, metadata

**Tiempo:** 45–75 min. **Prerrequisito:** módulo 1 (ya viste un JSON de query).

```
Estoy en el módulo 2 (docs/study/m02-chunking.md).
Guiame por el chunker. Quiero entender 512/64 y overlap.
No saltees a embeddings todavía.
```

---

## Hoy te quiero dejar defendiendo un compromiso

512 tokens de ventana y 64 de overlap **no son magia**. Son un trade-off
que este repo eligió y documentó. Vas a poder explicarlo como explicás
un tamaño de partición.

---

## Paso 1 — Por qué no indexamos el archivo entero

Dos razones, las dos de ingeniería:

1. **Contexto limitado.** El embedder y el LLM tienen una ventana. Un
   PDF de 40 páginas no entra entero de forma útil.
2. **Dilución.** Un embedding de un documento largo promedia muchos
   temas. Un detalle (un flag, una garantía ACID) se pierde. Chunks
   más chicos = vectores más “temáticos”.

Cortar mal también duele: si partís una oración clave al medio, el
retriever puede no recuperar el hecho. Por eso existe **overlap**.

---

## Paso 2 — Sliding window, en tokens

Este repo:

- `chunk_size = 512`
- `chunk_overlap = 64` (~12.5%)
- tokenizer: `tiktoken`, encoding `cl100k_base`

**Token ≠ palabra.** “Databricks” puede ser 1–3 tokens. Por eso no
cortamos por `len(text)`.

**Overlap:** los últimos 64 tokens del chunk N se repiten al inicio
del N+1. Analogía: window join / lookback para no perder la fila del
borde.

**Por qué no sentence-split:** docs técnicos mezclan ES/EN y bloques
de código; NLTK/spaCy se rompen. Está en `docs/ARCHITECTURE.md`.

---

## Paso 3 — El chunk es un record, no un string

En `app/core/chunker.py`, `Chunk` lleva `text`, `chunk_id` y
`metadata` (`source`, `filename`, `chunk_index`, …).

Eso es tu schema:

- PK: `chunk_id`
- linaje: `source`
- posición: `chunk_index`

Sirve para citar en la API y para evaluar con `expected_source`. El
ingest con `rebuild=True` es un batch que tira la colección y reescribe
(idempotencia tosca, como un overwrite de partición).

---

## Paso 4 — Recorremos el código juntos (orden)

1. `app/core/loaders.py` — PDF/MD/HTML/TXT → texto. Capa “extract”.
2. `Chunker.chunk_text` en `app/core/chunker.py` — el split.
3. `RAGPipeline.ingest` en `app/core/pipeline.py` — chunk → embed →
   `vector_store.add` + `bm25_store.index`. Hoy mirá **hasta** el
   chunking; los embeds son el módulo 3.
4. `scripts/ingest.py` — CLI.
5. `tests/test_chunker.py` — el contrato. **Leé los tests**: son la
   spec.

---

## Parada 2 — Aritmética de ventanas

Asumí un texto de **600 tokens**, size 512, overlap 64.

1. ¿Cuántos chunks salen? (dibujá el start offset: 0, luego
   `512 - 64 = 448`, etc.)
2. Si overlap = 0, ¿qué fallo de **recall** esperarías en una frase
   que cae justo en el corte?
3. Si overlap = 256, ¿qué costo pagás en índice (más chunks)?

Respondeme los tres números/ideas. Después verificamos con código.

---

## Laboratorio 2

Opción simple (preferida): corré `pytest tests/test_chunker.py -v` y
leé un test que falle si overlap ≥ size.

Opción extra: en un REPL, instanciá `Chunker` y chunké un markdown de
`data/sample/`. Contá chunks vs tokens aprox.

No cambies 512/64 en `config` todavía: eso es el experimento del
módulo 9.

---

## Criterio para pasar al módulo 3

- [ ] Explicás por qué tokens y por qué overlap.
- [ ] Nombrás 3 campos de metadata.
- [ ] Resolviste la aritmética de 600 tokens (aunque hayamos corregido
      juntos el off-by-one).

```
Cierre módulo 2: 600 tokens dan [N] chunks; overlap 0 fallaría así: …
Listo para el módulo 3.
```
