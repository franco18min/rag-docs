# Módulo 4 — BM25, híbrido y RRF

**Tiempo:** 60–90 min (hay una cuenta a mano). **Prerrequisito:** módulo 3.

```
Estoy en el módulo 4 (docs/study/m04-hibrido-rrf.md).
Quiero calcular RRF con un ejemplo. Guiame. No saltees al rerank.
```

---

## Hoy te quiero dejar escribiendo una fórmula

```
RRF(d) = Σ_retriever  1 / (k + rank(d))
```

con `k = 60`. Y sabiendo **cuándo** el vector solo no alcanza.

---

## Paso 1 — El agujero de los embeddings

Los vectores son buenos para parafrasis. Son flojos para **match
exacto**: un flag (`ENABLE_RERANK`), un setting de Spark, un código
de error, un número de versión.

**BM25** es ranking léxico (familia TF-IDF, el corazón de Lucene /
Elastic): premia términos raros y frecuentes en el doc, penaliza docs
largos. Si la query es el nombre literal de una función, BM25 suele
ganar.

---

## Paso 2 — Híbrido = dos ranked lists, no un join de facts

Este repo:

- Vector top-20
- BM25 top-20
- Fusionar

Analogía: dos índices, dos `ORDER BY`. El problema: **los scores no
viven en la misma escala**. BM25 no está acotado; cosine sí (aprox.
[-1, 1] o [0, 1] según implementación). Un `0.7 * vec + 0.3 * bm25`
es un infierno de calibración.

**RRF** tira los scores y usa solo el **puesto** (1, 2, 3, …).

Si un chunk aparece en **ambas** listas, suma dos términos `1/(k+rank)`
y sube. Eso es el “bonus por consenso”.

`k=60` viene del paper de Cormack et al. (SIGIR 2009), no de un
grid-search de este corpus.

---

## Paso 3 — Honestidad de *este* repo

En el README, ablation con 20 Q&A y 8 markdowns: **hybrid ≈ vector**
en Hit@K / MRR. Eso **no** prueba que el híbrido sea inútil ni que
“gane”. El n es chico y el corpus es semántico.

El híbrido se justifica por **clases de query** (léxicas vs
parafrásticas), no por esa tablita.

Leé ADR 0002 cuando termines la cuenta a mano.

---

## Paso 4 — Código

1. `app/core/bm25_store.py` — índice persistido, `query`.
2. `app/core/hybrid_search.py` — `search` llama a los dos; `_rrf_fusion`
   es el corazón. Leé el docstring de la fórmula.
3. `tests/test_hybrid_search.py` — casos de fusión. Tratá un test como
   ejemplo trabajado.
4. En `pipeline.query`, el paso 2 es hybrid **antes** del rerank.

---

## Parada 4 — Calculá antes de mirar el test

Listas (rank 1 = mejor):

- Vector: `A`, `B`, `C`
- BM25: `B`, `D`, `A`

`k = 60`.

1. RRF(A) = ?
2. RRF(B) = ?
3. ¿Quién queda primero, A o B, y por qué?

Mostrame las cuentas. Después las comparamos con `_rrf_fusion`.

---

## Laboratorio 4

1. Inventá una pregunta **léxica** (un token que aparezca en un sample,
   p.ej. un nombre de setting o de feature).
2. Inventá una **parafrástica** (mismas ideas, otras palabras).
3. Decime cuál debería favorecer BM25 y cuál el vector.
4. Leé la tabla de ablation del README **sin** concluir un ranking de
   arquitecturas.

Opcional: `pytest tests/test_hybrid_search.py -v`.

---

## Criterio para pasar al módulo 5

- [ ] Fórmula RRF escrita y ejemplo numérico correcto (o corregido).
- [ ] Sabés por qué no promediamos scores crudos.
- [ ] No usás la ablation de demo como prueba de superioridad.

```
Cierre módulo 4: RRF(A)=… RRF(B)=… gana … porque …
Listo para el módulo 5.
```
