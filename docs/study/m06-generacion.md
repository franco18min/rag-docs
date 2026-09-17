# Módulo 6 — Generación: prompt, temperatura, citas

**Tiempo:** 45–75 min. **Prerrequisito:** módulos 1 y 5 (viste un `answer`).

```
Estoy en el módulo 6 (docs/study/m06-generacion.md).
Quiero leer el prompt en voz alta y separar fallos de retrieval vs generación.
```

---

## Hoy te quiero dejar diagnosticando un fallo

Si la respuesta es mala, hay **dos culpables posibles**:

1. El retriever mandó chunks irrelevantes o incompletos.
2. El LLM redactó mal / inventó **pese a** un buen contexto.

Hasta este módulo el sistema era IR. Ahora entra Gemini: un transform
de `top-k chunks → string`.

---

## Paso 1 — El LLM no busca

`generator.generate(question, context_chunks)` recibe lo que ya
recuperaste. Si el contexto es basura, sale basura con buena prosa
(o una alucinación).

Por eso más adelante (módulo 7) se miden retrieval y generación
aparte. Como en DE: no mezclés un job de calidad de raw con un test
del dashboard.

---

## Paso 2 — Anatomía del prompt (`app/core/generator.py`)

1. **System instruction** — reglas: solo contexto; citas `[#N]`; no
   inventar flags/URLs; mismo idioma; camino de “no sé”.
2. **User template** — pregunta + chunks numerados.
3. **Temperatura 0.2** — menos aleatoriedad. Q&A técnico quiere
   repetibilidad, no creatividad.
4. **Parseo** de `[#N]` → objetos `Citation` con `source` y snippet.

Cada regla del system prompt existe por un fallo real. “Respondé en el
idioma de la pregunta” no es cosmética: el corpus es mixto ES/EN.

Analogía: el prompt es el contrato del transform (como un schema de
salida). Las citas son linaje.

---

## Paso 3 — Código

1. Constantes `SYSTEM_INSTRUCTION` y `USER_PROMPT_TEMPLATE`.
2. `Generator.generate` — cómo arma el contexto numerado.
3. Parseo de citas (regex `[#N]`).
4. `tests/test_generator_citations.py`.
5. ADR 0005 — por qué Flash-Lite y no GPT-4o.
6. `pipeline.query` pasos 4–5: generate + format citations.

---

## Parada 6

Leé `SYSTEM_INSTRUCTION` y, para **cada** regla numerada, escribí el
fallo que evita (una línea).

Después:

1. Si el retriever trae 5 chunks y solo 1 es útil, ¿eso es un fallo de
   Gemini o de context precision?
2. ¿Qué pasa si subís temperatura a 1.0 en eval?

---

## Laboratorio 6

1. Repetí una pregunta **ambigua** contra la API. ¿Las citas apuntan a
   chunks que realmente usaste al leer el `answer`?
2. (Opcional, branch) cambiá **una** frase del prompt, re-preguntá lo
   mismo, revertí. El prompt es un hiperparámetro, no un poema.

No mergees cambios de prompt “porque suena mejor” sin el módulo 7.

---

## Criterio para pasar al módulo 7

- [ ] Separás retrieval vs generación.
- [ ] Sabés dónde vive el prompt y por qué temperatura baja.
- [ ] Relacionás `[#N]` con `Citation`.

```
Cierre módulo 6: regla 1 evita […]; una pregunta ambigua citó […].
Listo para el módulo 7.
```
