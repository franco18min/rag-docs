# Módulo 7 — Evaluación (sin marketing)

**Tiempo:** 60–90 min. **Prerrequisito:** módulos 4 y 6.

```
Estoy en el módulo 7 (docs/study/m07-evaluacion.md).
Quiero leer métricas con escepticismo de data engineer.
No me dejes vender Context Precision 0.40.
```

---

## Hoy te quiero dejar leyendo números como leés un DQ report

Sin eval, RAG es demo. Con eval inflada, es CV theater. Este repo
documenta n chico a propósito.

---

## Paso 1 — Dos capas, dos scripts

**Retrieval** — `scripts/ablation.py`

- Hit@K: ¿el `expected_source` está en el top K?
- MRR: promedio de `1/posición` del primer acierto.
- Ground truth: campo `expected_source` en `data/eval/qa_set.json`.
  **No** adivina el archivo por el texto de la pregunta.

**Generación** — `scripts/evaluate_light.py`

- LLM-as-judge, **1 call por pregunta**.
- Faithfulness / answer relevancy (aproximados).
- Precision/recall de contexto en el camino light **no son un logro**.

**RAGAS full** (`scripts/evaluate.py`) **no está soportado**. Si
explota por langchain/datasets, es esperado.

---

## Paso 2 — Diccionario de métricas (light)

| Métrica | Pregunta que hace |
|---|---|
| Faithfulness | ¿Las claims están en el contexto o inventó? |
| Answer relevancy | ¿Respondió *esta* pregunta? |
| Context precision | ¿Los chunks traídos eran pertinentes? |
| Context recall | ¿Trajimos el hecho necesario? |

Heurística (`docs/EVALUATION.md`):

- Faithfulness baja + retrieval alto → prompt/modelo.
- Recall bajo → chunking o top-k se comió el hecho.
- Relevancy alta + faithfulness baja → lindo y no grounded.

**Nunca** compares estos números con MTEB/BEIR como el mismo
experimento.

Analogía: `qa_set.json` = tests de expected values. Ablation = A/B de
motores. Judge = validator heurístico, no SLA.

---

## Paso 3 — Código y datos

1. Abrí `data/eval/qa_set.json` — 3 ítems. Verificá que
   `expected_source` exista en `data/sample/`.
2. `docs/EVALUATION.md` entero (es la guía, no el paper).
3. Ojeá `scripts/ablation.py` (cómo usa `expected_source`).
4. Disclaimer al tope de `scripts/evaluate.py`.

---

## Parada 7

1. Hit@5 = 0.90 con n=20. ¿Cuántas preguntas fallan el top-5?
2. ¿Por qué hybrid ≈ vector **no** cierra el debate híbrido?
3. Si faithfulness sube y precision baja, ¿es un win de producto?

---

## Laboratorio 7

1. (Con ingest hecho)  
   `python scripts/ablation.py --eval-set data/eval/qa_set.json`  
   Anotá Hit@1 de vector vs hybrid. Sin tweet.
2. Escribí **una** pregunta nueva con `expected_source` real. Pegamela.
   Eso enseña más que diez papers.
3. Opcional: `python -m scripts.evaluate_light` y leé
   `EVALUATION.md` al lado de los números.

---

## Criterio para pasar al módulo 8

- [ ] Definís Hit@K y MRR en una frase cada uno.
- [ ] Recitás n, corpus chico, y que el judge es ruidoso.
- [ ] Agregaste o diseñaste al menos 1 Q&A con source.

```
Cierre módulo 7: Hit@1 vector=… hybrid=…; mi pregunta nueva es … → …
Listo para el módulo 8.
```
