# Guía de evaluación

Este repo mide retrieval y generación sobre un **corpus de demo chico**
(`data/sample/`, 8 markdowns). Los números del README son **históricos**
para ese corpus; no implican calidad de producción ni que hybrid
“gane” frente a vector.

**Camino soportado:** `python scripts/evaluate_light.py` (LLM-as-judge,
una call por pregunta).

**No soportado:** RAGAS full vía `scripts/evaluate.py`. Ese script
imprime un disclaimer y suele fallar por conflictos de versiones de
langchain / datasets. Tratá esos fallos como esperados.

Cada Q&A en `data/eval/qa_set.json` incluye `expected_source` (nombre de
archivo markdown). La ablation usa ese campo; no adivina la fuente a
partir del texto de la pregunta.

## Las cuatro métricas (judge light)

Los targets de abajo son **pistas diagnósticas**, no claims de CV.
Precision y recall con n≈20 y un LLM judge **no** son un logro.

### 1. Faithfulness

**Pregunta**: ¿la respuesta es fiel al contexto recuperado, o el modelo
está alucinando?

El judge light puntúa esto 0–1 según si las claims están soportadas en
el contexto (no es el pipeline oficial de descomposición de RAGAS).

**Qué implica faithfulness bajo**:
- El prompt es demasiado permisivo (el modelo inventa)
- Chunks de baja calidad en el contexto
- Los límites de chunk parten contexto importante a la mitad

**Fixes**:
- Bajar la temperatura del generador
- Agregar instrucciones explícitas de "responder SOLO desde el contexto"
- Subir el overlap en el chunker

### 2. Context Precision

**Pregunta**: ¿los chunks que recuperamos son realmente relevantes a la
pregunta?

En este corpus el score light histórico es **bajo (~0.40)**. Eso es
judge estricto + n chico, no un ranking del retriever.

**Qué puede implicar context precision bajo**:
- Top-k alto (chunks irrelevantes en la ventana)
- El judge penaliza respuestas largas/exhaustivas

### 3. Context Recall

**Pregunta**: ¿recuperamos la información necesaria para responder la
pregunta?

Score light histórico **~0.59** con n=20. Misma salvedad: no lo vendas
como victoria o derrota de retrieval.

**Qué puede implicar context recall bajo**:
- El chunking parte hechos a través de los límites
- Top-k demasiado bajo
- El ground truth es más específico que los snippets recuperados

### 4. Answer Relevancy

**Pregunta**: ¿la respuesta aborda realmente la pregunta hecha?

El camino light lo aproxima con un score de LLM (no el cosine de RAGAS
sobre preguntas sintéticas).

## Cómo leer los números juntos

| Faithfulness | Context Precision | Context Recall | Answer Relevancy | Diagnóstico (heurística) |
|---|---|---|---|---|
| Bajo | Alto | Alto | Bajo | Problema de generación (prompt o modelo) |
| Alto | Bajo | Alto | Alto | Ventana/top-k o severidad del judge |
| Alto | Alto | Bajo | Alto | Chunking / hechos faltantes |
| Bajo | Bajo | Bajo | Bajo | Desajuste de corpus, modelo o chunking |

Ablation Hit@K / MRR en esta demo: **hybrid ≈ vector**. El rerank puede
bajar Hit@1 y sumar latencia. Ver las tablas del README; no trates una
corrida como ranking de arquitecturas.

## Cómo correrlo (soportado)

```bash
# Hand-curated set (preferred; has expected_source)
# data/eval/qa_set.json is already populated for the sample corpus

# Light evaluation (supported)
python scripts/evaluate_light.py

# Retrieval ablation (Hit@K / MRR from expected_source)
python scripts/ablation.py --eval-set data/eval/qa_set.json
```

Opcional: generar Q&A extra con Gemini y después agregar `expected_source`
vos:

```bash
python -m scripts.generate_eval_set --collection spark_docs --output data/eval/qa_set.json
```

RAGAS full (no soportado):

```bash
python -m scripts.evaluate \
  --collection spark_docs \
  --eval-set data/eval/qa_set.json \
  --output data/eval/results.json
```

## Armar un buen set de Q&A

- Incluí **`expected_source`** que coincida con un markdown de sample
  (`delta_lake_intro.md`, `retrieval.md`, …)
- El ground truth tiene que ser respondible desde los docs indexados
- Mezclá preguntas definicionales / procedimentales / comparativas
- n=20 sobre 8 archivos alcanza para un smoke-test, no para rankear sistemas

## Cuándo volver a correr

- Después de cambiar chunking, embeddings, retriever, rerank o prompt
- Diff contra el baseline anterior sobre el **mismo** eval set
- Si algunas métricas suben y otras bajan, es un trade-off de producto
