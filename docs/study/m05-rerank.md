# Módulo 5 — Rerank (cross-encoder, opt-in)

**Tiempo:** 40–60 min. **Prerrequisito:** módulo 4.

```
Estoy en el módulo 5 (docs/study/m05-rerank.md).
Quiero entender bi-encoder vs cross-encoder y por qué ENABLE_RERANK=false.
```

---

## Hoy te quiero dejar apagando una feature con criterio

Rerank **no** es “más AI = mejor”. En este corpus empeoró Hit@1 y
explotó la latencia. Default: `ENABLE_RERANK=false`.

---

## Paso 1 — Dos modelos, dos costos

| | Bi-encoder (BGE-M3) | Cross-encoder (BGE-reranker-base) |
|---|---|---|
| Input | query y chunk **por separado** | el **par** (query, chunk) junto |
| Uso | índice + kNN | rescoring de pocos candidatos |
| Velocidad | rápido | ~100× más lento |
| Precisión en la cabeza | buena | suele ser mejor *en benchmarks de IR* |

El híbrido te da ~20 candidatos baratos. El cross-encoder los reordena
y se queda con top-5 para el LLM.

Analogía DE: filtro SQL barato → modelo de scoring caro sobre 20 filas.
Si el scoring no mueve la métrica de negocio, se apaga.

---

## Paso 2 — Qué pasó *acá* (no en el paper)

ADR 0003 y el README: con rerank, Hit@1 **bajó** (0.90 → 0.85) y la
latencia pasó de ~80 ms a ~5 s en CPU. n=20, 8 markdowns.

Un paper de nDCG en BEIR **no se copia** a este corpus. Por eso el ADR
está “aceptado condicionalmente”: existe el código, no es el default.

---

## Paso 3 — Código

1. `app/core/reranker.py` — `CrossEncoder`; `_hybrid_slice` no debe
   dejarte la lista vacía si había candidatos (`tests/test_reranker.py`).
2. `app/config.py` — `ENABLE_RERANK`.
3. `pipeline.query` paso 3: `reranker.rerank(...)` **siempre se llama**
   en código; el reranker internamente puede devolver el orden híbrido
   si está off. Confirmalo leyendo `rerank()`: no asumas, leé.
4. `docs/adr/0003-rerank-cross-encoder.md` — sección “cuándo
   reconsiderar”.

---

## Parada 5

1. ¿Por qué no corremos el cross-encoder contra los 10k chunks?
2. Si un paper dice +20% nDCG, ¿lo citarías en el README de este MVP?
   ¿Por qué sí o no?
3. Leé `rerank()` y respondé: con `ENABLE_RERANK=false`, ¿qué lista
   llega al generador?

---

## Laboratorio 5

Leé el ADR 0003 entero (es corto). Anotá las señales para
reconsiderarlo.

Opcional (siente el costo): activá rerank, una query, mirá `latency_ms`,
apagalo. No hace falta “ganar calidad”.

---

## Criterio para pasar al módulo 6

- [ ] Distinguís bi-encoder vs cross-encoder.
- [ ] Sabés que el default es off y por qué en *este* corpus.
- [ ] No vendés rerank en una entrevista como obligatorio.

```
Cierre módulo 5: con rerank off, al generador llega […].
Listo para el módulo 6.
```
