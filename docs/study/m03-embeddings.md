# Módulo 3 — Embeddings y búsqueda vectorial

**Tiempo:** 45–75 min. **Prerrequisito:** módulo 2 (sabés qué es un chunk).

```
Estoy en el módulo 3 (docs/study/m03-embeddings.md).
Explicame embeddings como si fueran una proyección; después el código.
No saltees a BM25.
```

---

## Hoy te quiero dejar con esta distinción

**Buscar palabras** (grep, LIKE, BM25) vs **buscar significado**
(vecinos en un espacio numérico). El índice vectorial es lo segundo.
Se construye **offline**; en el query solo embeddeás la pregunta.

---

## Paso 1 — Qué es un embedding

Una función `texto → R^d`. Acá **d = 1024** (BGE-M3).

Dos textos “parecidos en significado” quedan **cerca**. “Garantías ACID
de Delta” y “transacciones atómicas en Delta Lake” pueden matchear
aunque compartan pocos tokens.

No es magia de Google: es un modelo (BGE-M3) que corre **en tu CPU**
vía `sentence-transformers`. Costo por query de API de embeddings: $0.
Costo real: RAM, latencia, descarga del modelo.

---

## Paso 2 — Bi-encoder (por qué el índice es rápido)

```
offline:  embed(chunk_i) → d_i   → se guarda en Chroma
online:   embed(pregunta) → q
          score_i = cosine(q, d_i)
          devolver top-k
```

**Bi-encoder** = query y documento se embeddean **por separado**. Podés
precomputar todos los `d_i`. Eso es indexable, como precomputar una
columna.

**Coseno:** ángulo entre vectores. Cerca de 1 = muy similares. Chroma
en este repo usa cosine.

**Normalización** (`normalize=True` en `Embedder.embed`): vectores de
norma 1. Entonces cosine ≡ producto punto. El diseño elige cosine +
normalizar para consistencia.

El `score` de una cita **no es P(correcto)**.

---

## Paso 3 — Analogía DE

Chroma = “dev warehouse” de vectores: proceso local, persistencia a
disco, cero ops. No sirve para GROUP BY; sirve para kNN.

Databricks Vector Search = backend remoto opcional (Unity Catalog).
La app elige backend con `VECTOR_STORE_BACKEND`. **No hay pgvector**
en este repo.

ADR 0001 (por qué BGE-M3) y ADR 0004 (por qué no acoplar Chroma).

---

## Paso 4 — Código, en este orden

1. `app/core/embedder.py` — singleton (cargar el modelo es caro).
   `embed` vs `embed_query`.
2. `app/core/pipeline.py` — en `ingest`, `embedder.embed(...)` +
   `vector_store.add(...)`. En `query`, `embed_query` **antes** del
   hybrid search.
3. `app/core/vector_store.py` — wrapper Chroma.
4. `app/core/store_factory.py` — chroma vs databricks. Solo ojealo.
5. `docs/adr/0001-bge-m3-embedding-model.md` — la decisión, no el
   marketing del paper.

---

## Parada 3

1. ¿Por qué embeddeamos los chunks en ingest y no en cada query?
2. Si dos chunks tienen cosine 0.99, ¿significa que el LLM va a
   citarlos bien?
3. BGE-M3 vs `text-embedding-3-small` de OpenAI: ¿qué ganás y qué
   pagás en *este* MVP?

---

## Laboratorio 3

Releé una respuesta del módulo 1. Mirà `citations[].score`. Anotá el
rango. Repetirme: “esto es ranking, no certeza”.

Si querés ir un paso más: leé `embed_query` y confirmá que usa el
mismo modelo que `embed`.

---

## Criterio para pasar al módulo 4

- [ ] Explicás bi-encoder y por qué el índice es offline.
- [ ] No tratás cosine como probabilidad.
- [ ] Sabés que Chroma es el default y Databricks es adapter.

```
Cierre módulo 3: [respuestas parada]. Listo para el módulo 4.
```
