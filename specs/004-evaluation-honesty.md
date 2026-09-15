# A4 — Honestidad de evaluación

## Contexto

`qa_set.json` / template **sin** `expected_source`. `ablation.py` adivina fuentes. README/EVALUATION: RAGAS full, “hybrid gana”, “top 10%”, precision/recall como logro, corpus implícito 50–100. Camino real: `evaluate_light.py`.

## Toca

- `data/eval/qa_set.json`
- `data/eval/qa_set_template.json`
- `scripts/ablation.py`
- `scripts/evaluate.py`
- `scripts/evaluate_light.py` (disclaimer / camino soportado)
- `docs/EVALUATION.md`
- Tablas de métricas en `README.md`

## No toca

Pipeline core, generator, BM25/hybrid/rerank, CI tests de A5.

## Comportamiento

- Cada Q&A: `expected_source` (path o stem del markdown A1).
- `ablation.py` **deja de adivinar**; usa `expected_source`.
- Tablas README: históricas y/o corpus chico; **hybrid ≈ vector** si eso miden los números; **no** “hybrid gana”.
- Quitar “top 10%”.
- Precision/recall: honestos (definición + n chico) **o** no venderlos como logro.
- `evaluate.py`: disclaimer **RAGAS full no soportado**.
- Camino soportado documentado: `evaluate_light.py`.

## AC verificables

- [ ] Todas las entradas de `qa_set.json` y template tienen `expected_source`.
- [ ] Ablation no infiere fuente por heurística de texto.
- [ ] README no afirma “hybrid gana” ni “top 10%”.
- [ ] EVALUATION + `evaluate.py` dicen RAGAS full no soportado; light es el path.
- [ ] Diff no cambia pipeline core.

## Riesgos

- `expected_source` desalineado con stems A1.
- Ablation sigue usando filenames de chunks si metadata `source` no coincide.
