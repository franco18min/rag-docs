# Plan de estudio: de data engineer a RAG (con este repo)

Este documento es un plan **desde cero en AI**, pensado para alguien que ya
sabe pipelines, SQL, Spark, calidad de datos y producción. El objetivo no
es “aprender machine learning entero”: es entender **por qué existe este
sistema**, **qué problema resuelve cada pieza**, y **cómo leer y modificar
el código** de `rag-docs`.

El hilo conductor es **RAG** (Retrieval-Augmented Generation): recuperar
fragmentos de documentación y pedirle a un LLM que responda **solo** con
eso. Eso es exactamente lo que hace este repo.

**Cómo usarlo**

- Cada módulo tiene: concepto, analogía de data engineering, dónde vive
  en el código, ejercicio, y criterio de “ya lo entendí”.
- Leé el código **antes** de cambiarlo. El plan asume que corrés el
  proyecto localmente (ver el README).
- No hace falta GPU. Los embeddings y el reranker corren en CPU; Gemini
  es una API gratuita.

---

## Mapa mental (el puente DE → AI)

| Lo que ya sabés | Equivalente en este sistema |
|---|---|
| ETL / ingestión | Loaders + chunking (`scripts/ingest.py`, `app/core/loaders.py`, `chunker.py`) |
| Modelo de datos / schema | Metadata de cada chunk + schemas Pydantic (`app/models/`) |
| Índice (Parquet, Delta, Elastic) | Vector store (Chroma) + índice BM25 |
| Join / union de fuentes | RRF: fusiona ranking vector + ranking léxico |
| Calidad de datos / tests | Eval set + Hit@K / MRR + LLM-as-judge |
| Orquestación (Airflow, Jobs) | `RAGPipeline` en `app/core/pipeline.py` |
| API de servicio | FastAPI (`app/main.py`) |
| Dashboard / demo | Streamlit (`app/streamlit_app.py`) |
| ADR de plataforma | `docs/adr/` |

La diferencia grande: en data engineering el “resultado” suele ser una
tabla. Acá el resultado es **texto generado**, y el riesgo principal es
**alucinación** (afirmar algo que no está en los documentos). RAG existe
para bajar ese riesgo: el modelo no “recuerda” tu corpus; **lo lee** en
el momento de la pregunta.

---

## Glosario mínimo (leelo una vez, volvé cuando haga falta)

- **LLM (Large Language Model)**: red entrenada para predecir el siguiente
  token. Es un generador de texto, no una base de hechos. Gemini Flash-Lite
  es el LLM de este proyecto.
- **Token**: unidad de texto que usa el modelo (subpalabra, no siempre
  “palabra”). `tiktoken` cuenta tokens; el chunker corta en 512 tokens.
- **Prompt**: instrucciones + pregunta + contexto que le mandás al LLM.
  El prompt de este repo está en `app/core/generator.py`.
- **Embedding**: vector numérico (acá 1024 dimensiones) que representa
  significado. Dos textos “parecidos” quedan cerca en ese espacio.
- **Similitud coseno**: ángulo entre dos vectores. Cerca de 1 = muy
  similares. Chroma busca vecinos por cosine.
- **Bi-encoder**: embeddea query y documento **por separado** (rápido,
  indexable). BGE-M3 es un bi-encoder.
- **Cross-encoder**: mira el **par** (pregunta, chunk) junto (más preciso,
  lento). El reranker es un cross-encoder.
- **Retrieval**: recuperar los chunks más relevantes para una pregunta.
- **Generation**: el LLM escribe la respuesta usando esos chunks.
- **Grounding**: atar cada afirmación al contexto recuperado. Las citas
  `[#N]` son grounding visible.
- **Alucinación**: el modelo inventa. Faithfulness mide (de forma
  aproximada) si eso pasó.
- **BM25**: ranking clásico por palabras (TF-IDF sofisticado). Bueno para
  nombres de función, flags, códigos de error.
- **RRF (Reciprocal Rank Fusion)**: suma `1/(k + rank)` de cada retriever.
  No calibra scores; fusiona **posiciones**.
- **Hit@K**: ¿el documento correcto está en los primeros K resultados?
- **MRR (Mean Reciprocal Rank)**: promedio de `1/posición` del primer
  acierto. Premia que el correcto quede arriba.
- **LLM-as-judge**: usar un LLM para puntuar otro LLM. Barato y ruidoso;
  no es un lab de IR.

---

## Orden del plan

1. Qué es (y no es) la IA generativa
2. Correr el sistema de punta a punta
3. Ingestión y chunking (tu zona de comfort)
4. Embeddings y vector search
5. BM25 + híbrido + RRF
6. Rerank (opt-in) y el trade-off latencia/calidad
7. Generación, prompts y citas
8. Evaluación honesta
9. API, config y abstracción de store
10. Cerrar el círculo: un experimento propio

Estimación de esfuerzo: **un módulo por sesión** (45–90 min de lectura +
código). Diez sesiones cubren el MVP. No es un bootcamp de deep learning.

---

## Módulo 0 — Mental model: por qué RAG y no “un chatbot”

### Concepto

Un LLM **no tiene** tus PDFs internamente de forma confiable. Si le
preguntás “¿qué garantías ACID da Delta Lake?” sin contexto, puede
mezclar memoria de entrenamiento, inventar versiones, o alucinar flags.

Tres patrones típicos:

1. **Solo LLM**: barato de implementar, frágil en docs internas.
2. **Fine-tuning**: reentrenar/adaptar pesos. Caro, lento de actualizar
   cuando cambia la documentación. **No es este repo.**
3. **RAG**: indexás docs → al query recuperás N fragmentos → el LLM
   responde con esos fragmentos. Actualizar docs = re-ingerir, no
   reentrenar.

Este proyecto es (3).

### Analogía DE

Fine-tuning es como materializar un cubo enorme y rehacerlo cada vez que
cambia el origen. RAG es más parecido a **query-time join**: guardás los
hechos (chunks) y al preguntar traés las filas relevantes.

### Lectura

- `README.md` (sección arquitectura y “¿Por qué este proyecto?”)
- `docs/ARCHITECTURE.md` (vista general + “Qué NO está a propósito”)

### Criterio de salida

Podés explicar en una frase: *“RAG recupera contexto y el LLM lo usa;
no ‘aprende’ el corpus.”*

---

## Módulo 1 — Levantar el MVP y mirar un request

### Objetivo

Tener un loop cerrado: ingest → API → una pregunta → JSON con `answer` y
`citations`.

### Pasos

Seguí el README (venv, `.env` con `GOOGLE_API_KEY`, ingest de
`data/sample/`, `uvicorn`, opcional Streamlit).

### Qué observar en la respuesta

Campos de `QueryResponse` (`app/models/response.py`):

- `answer`: texto del LLM
- `citations`: fuente + snippet + score
- `latency_ms`: presupuesto de producto
- `model`: `gemini-flash-lite-latest`
- `chunks_retrieved`: cuántos chunks llegaron al generador
- `trace_id`: siempre `None` (Langfuse no está)

### Ejercicio

Hacé **dos** preguntas:

1. Algo que **está** en el corpus (Medallion, time travel, BGE-M3).
2. Algo que **no está** (“¿cuál es el salario del CEO de Databricks?”).

Esperá en (2) el camino de “no encuentro esa información…”. Eso es el
prompt trabajando, no magia del modelo.

### Criterio de salida

Sabés arrancar el stack y distinguir una respuesta grounded de una
pregunta fuera de corpus.

---

## Módulo 2 — Ingestión: loaders, chunks, metadata

### Concepto: chunking

El LLM y el embedder tienen un **contexto limitado**. Además, si
embeddeás un documento entero, un detalle chico se diluye en el vector.
Por eso cortamos el texto en **chunks**.

Este repo usa **sliding window**:

- `chunk_size = 512` tokens
- `chunk_overlap = 64` tokens (~12.5%)

El overlap existe para que una idea que cae en el borde de un chunk
también aparezca (parcialmente) en el siguiente. Es el mismo espíritu que
un window join: no querés perder la fila que está en el límite.

**Por qué tokens y no caracteres:** los modelos piensan en tokens.
`tiktoken` (`cl100k_base`) alinea el corte con esa unidad.

**Por qué no split “inteligente” por oraciones en este MVP:** docs
técnicos mezclan español/inglés y bloques de código; los sentence
splitters se rompen. Está explicado en `docs/ARCHITECTURE.md`.

### Metadata

Cada chunk no es solo texto. Lleva `source`, `filename`, `chunk_index`,
etc. Eso permite:

- citar la fuente en la API
- evaluar con `expected_source`
- filtrar (hoy el camino principal no filtra por metadata, pero el
  diseño lo deja listo)

### Analogía DE

Chunker = particionar un archivo grande en records con primary key
(`chunk_id`) y columnas de linaje (`source`). El ingest es un job batch
idempotente si `rebuild=True`.

### Código

| Archivo | Rol |
|---|---|
| `app/core/loaders.py` | PDF / MD / HTML / TXT → texto |
| `app/core/chunker.py` | sliding window + metadata |
| `scripts/ingest.py` | CLI de ingestión |
| `app/core/pipeline.py` → `ingest()` | orquesta chunk → embed → index |
| `tests/test_chunker.py` | contratos del chunker |

### Ejercicios

1. Leé `Chunker.chunk_text` y `tests/test_chunker.py`.
2. En una hoja, dibujá un texto de 600 tokens con overlap 64: ¿cuántos
   chunks salen? Verificá con un script de 10 líneas o un test local.
3. Cambiá mentalmente overlap a 0: ¿qué fallo de recall esperarías?

### Criterio de salida

Podés defender 512/64 (compromiso, no dogma) y decir qué metadata viaja
con cada chunk.

---

## Módulo 3 — Embeddings y búsqueda vectorial

### Concepto

Un **embedding** es una función `texto → R^d`. Acá `d = 1024` (BGE-M3).

La **búsqueda vectorial** no busca palabras: busca vecinos en ese
espacio. “ACID de Delta” y “transacciones atómicas en Delta Lake”
pueden matchear aunque no compartan tokens.

**Normalización:** si los vectores tienen norma 1, similitud coseno ≡
producto punto. El embedder normaliza por default.

**Bi-encoder (lo que usa el índice):**

```
embed(query)     → q
embed(chunk_i)   → d_i     (offline, una vez)
score = cosine(q, d_i)
```

Es rápido porque los `d_i` ya están en Chroma. El costo en query es
embeddear la pregunta + kNN.

**Por qué BGE-M3 y no OpenAI embeddings:** local, $0, multilingüe,
contexto largo. Costo: RAM y latencia de CPU. Ver ADR 0001.

### Analogía DE

El vector store es un índice no relacional optimizado para kNN, no para
agregaciones. Chroma en este repo es el “dev warehouse”: persistencia
local, cero ops. Databricks Vector Search es el “prod-ish remoto”
opcional (ADR 0004).

### Código

| Archivo | Rol |
|---|---|
| `app/core/embedder.py` | singleton SentenceTransformer BGE-M3 |
| `app/core/vector_store.py` | Chroma (cosine) |
| `app/core/vector_store_databricks.py` | adapter Databricks |
| `app/core/store_factory.py` | `VECTOR_STORE_BACKEND` |
| `docs/adr/0001-bge-m3-embedding-model.md` | decisión |
| `docs/adr/0004-vector-store-abstraction.md` | por qué no acoplar Chroma |

### Ejercicios

1. Leé `Embedder.embed` y notá `normalize=True`.
2. Pensá: si **no** normalizás y Chroma usa cosine, ¿cambia el ranking?
   (En cosine clásico, no; en L2 sí. Este diseño elige cosine +
   normalizar para consistencia.)
3. Corré una query y mirá `score` de las citas. No lo trates como
   probabilidad; es similitud/ranking.

### Criterio de salida

Podés explicar la diferencia entre “buscar palabras” y “buscar
significado”, y por qué el índice se construye **offline**.

---

## Módulo 4 — BM25, híbrido y RRF

### Concepto

Los embeddings fallan en match **exacto**: `ENABLE_RERANK`,
`spark.sql.shuffle.partitions`, un código de error, una versión.

**BM25** rankea documentos por solapamiento de términos, con saturación
de frecuencia y penalización por documentos largos. Es el abuelo de
Elasticsearch / Lucene.

**Híbrido** = correr los dos retrievers (top-20 cada uno) y **fusionar**.

**Por qué RRF y no un promedio ponderado de scores:**

- BM25 no tiene la misma escala que cosine.
- Calibrar pesos (`0.7 * vec + 0.3 * bm25`) es un infierno operativo.
- RRF solo usa el **puesto** en cada lista:

```
RRF(d) = Σ_r  1 / (k + rank_r(d))
```

`k=60` (paper de Cormack, SIGIR 2009). Un chunk que aparece en **ambos**
rankings suma dos términos y sube.

**Dato honesto de este repo:** en el corpus de demo (8 markdowns, 20
Q&A), **hybrid ≈ vector** en Hit@K / MRR. Eso no “desmuestra” el
híbrido; el n es chico y el corpus es semántico. El híbrido se justifica
por **clases de query** (léxicas vs semánticas), no por esa tabla.

### Analogía DE

Dos índices (como tener Elastic + un índice semántico). RRF es un
`UNION` de rankings con un score de fusión, no un join de facts.

### Código

| Archivo | Rol |
|---|---|
| `app/core/bm25_store.py` | índice BM25 persistido |
| `app/core/hybrid_search.py` | RRF |
| `tests/test_hybrid_search.py` | fusión y desempates |
| `docs/adr/0002-hybrid-search-bm25-vector.md` | decisión |

### Ejercicios

1. Tomá dos listas inventadas de ranks y calculá RRF a mano con k=60.
   Compará con `_rrf_fusion`.
2. Inventá una pregunta **léxica** (un flag de config que aparezca en
   un sample) y una **parafrástica**. ¿Cuál debería favorecer BM25?
3. Leé la ablation del README **sin** concluir “hybrid gana”.

### Criterio de salida

Podés escribir la fórmula RRF y decir cuándo el vector solo no alcanza.

---

## Módulo 5 — Rerank: cross-encoder opt-in

### Concepto

Después del híbrido tenés ~20 candidatos baratos pero “toscos”. Un
**cross-encoder** toma `(pregunta, chunk)` y predice relevancia con
atención cruzada. Más preciso en la cabeza del ranking; ~100× más lento
que un bi-encoder. Por eso: **solo top-20 → top-5**.

En **este** corpus, habilitar rerank **bajó Hit@1** y multiplicó
latencia (~88 ms → ~5 s en CPU). Default: `ENABLE_RERANK=false`.
Eso es una lección de producto, no un bug: un paper de nDCG en
benchmarks públicos no se copia a 8 markdowns.

### Analogía DE

Es un segundo stage de ranking (como un modelo de scoring después de un
filtro SQL barato). Si el stage caro no mejora la métrica de negocio,
se apaga.

### Código

| Archivo | Rol |
|---|---|
| `app/core/reranker.py` | CrossEncoder BGE-reranker-base |
| `app/config.py` | `ENABLE_RERANK` |
| `tests/test_reranker.py` | no vaciar candidatos |
| `docs/adr/0003-rerank-cross-encoder.md` | aceptación condicional |

### Ejercicios

1. Leé el ADR 0003 completo. Anotá “cuándo reconsiderar”.
2. (Opcional) Activá rerank, medí latencia en una query, desactivalo.
   No hace falta “ganar calidad”; hace falta **sentir** el costo.

### Criterio de salida

Distinguís bi-encoder vs cross-encoder y no vendés rerank como default.

---

## Módulo 6 — Generación: el LLM, el prompt y las citas

### Concepto

Hasta acá el sistema es IR (information retrieval). El LLM es el
**último stage**: redacta.

Piezas del prompt en `generator.py`:

1. **System instruction**: reglas (solo contexto, citas `[#N]`, no
   inventar flags, mismo idioma, camino de “no sé”).
2. **User prompt**: pregunta + chunks numerados.
3. **Temperatura 0.2**: menos creatividad, más determinismo.
4. **Parseo de `[#N]`**: mapear marcadores del texto a `Citation`
   objetos con `source` y snippet.

**Temperatura:** controla aleatoriedad del sampling. Baja = más repetible
(útil en Q&A técnico y eval).

**El LLM no “busca”.** Si el retriever le mandó basura, va a redactar
basura con buena prosa (o inventar). Por eso se evalúa retrieval y
generación **por separado**.

### Analogía DE

El generador es un transform que consume un dataframe chico (top-k
chunks) y emite un string. El prompt es el contrato de ese transform.
Las citas son tests de linaje: cada claim debería tener `source`.

### Código

| Archivo | Rol |
|---|---|
| `app/core/generator.py` | Gemini + prompt + parseo de citas |
| `app/core/pipeline.py` → `query()` | retrieval → (rerank) → generate |
| `tests/test_generator_citations.py` | `[#N]` → fuentes |
| `docs/adr/0005-gemini-flash-lite.md` | por qué este modelo |

### Ejercicios

1. Leé `SYSTEM_INSTRUCTION` en voz alta. Cada regla existe para un
   fallo concreto (alucinación, idioma, URLs inventadas).
2. Preguntá algo ambiguo y fijate si cita chunks irrelevantes: eso es
   context precision, no “el modelo es tonto”.
3. Cambiá **una** frase del prompt (en un branch) y re-preguntá lo
   mismo. El prompt es un hyperparámetro.

### Criterio de salida

Separás fallos de retrieval vs fallos de generación. Sabés dónde está
el prompt y por qué hay temperatura baja.

---

## Módulo 7 — Evaluación: métricas sin marketing

### Concepto

Sin eval, RAG es demo theater. Con eval mal leída, es CV theater. Este
repo es explícitamente **honesto** con n chico.

**Dos capas:**

1. **Retrieval** (`scripts/ablation.py`): Hit@K y MRR usando
   `expected_source` en `data/eval/qa_set.json`. No adivina la fuente
   por el texto de la pregunta.
2. **Generación** (`scripts/evaluate_light.py`): un LLM puntúa
   faithfulness y relevancy (1 call por pregunta). Precision/recall de
   contexto en el camino light **no se venden como logro**.

**RAGAS full** (`scripts/evaluate.py`) **no está soportado** (conflictos
de deps). Si falla, es esperado.

**Cómo leer juntas** (detalle en `docs/EVALUATION.md`):

- Faithfulness baja + retrieval alto → prompt o modelo inventa.
- Context recall bajo → chunking o top-k se comió el hecho.
- Answer relevancy alta y faithfulness baja → responde “lindo” pero no
  grounded.

**Nunca** compares tus números con papers de MTEB/BEIR como si fueran
el mismo experimento.

### Analogía DE

`qa_set.json` es tu conjunto de tests de data quality con expected
values. Ablation es A/B de motores de búsqueda. LLM-as-judge es un
check aproximado, como un validator heurístico: útil para regresiones,
no para certificar SLA.

### Código / docs

| Archivo | Rol |
|---|---|
| `data/eval/qa_set.json` | 20 Q&A + `expected_source` |
| `scripts/ablation.py` | vector vs hybrid vs hybrid+rerank |
| `scripts/evaluate_light.py` | judge light |
| `scripts/generate_eval_set.py` | Q&A sintéticas (después curar a mano) |
| `docs/EVALUATION.md` | cómo interpretar |

### Ejercicios

1. Abrí 3 items de `qa_set.json`. Verificá que el `expected_source`
   existe en `data/sample/`.
2. Corré `python scripts/ablation.py --eval-set data/eval/qa_set.json`
   (después de ingest). Anotá Hit@1, no el ranking de Twitter.
3. Escribí **una** pregunta nueva con `expected_source`. Eso enseña más
   que diez papers.

### Criterio de salida

Podés explicar Hit@K y MRR, y recitar las limitaciones (n, corpus,
judge). No usás Context Precision 0.40 como trophy.

---

## Módulo 8 — El sistema como producto: API, config, CI

### Concepto

Un pipeline de notebook no es un sistema. Acá hay:

- **Settings** centralizados (`app/config.py`, Pydantic): chunk size,
  modelo, backend, flags.
- **FastAPI**: `/health`, collections, `/query`, ingest.
- **Inyección de dependencias** en `RAGPipeline`: los tests pasan
  fakes (mismo patrón que mockear un Spark session).
- **CI**: ruff + mypy + pytest (`.github/workflows/ci.yml`).
- **Hueco consciente:** `app/observability/` vacío; no hay tracing.

### Código

| Archivo | Rol |
|---|---|
| `app/config.py` | knobs |
| `app/main.py` | HTTP |
| `app/streamlit_app.py` | UI |
| `tests/test_api.py`, `tests/test_pipeline_query.py` | contratos |
| `docs/DEPLOY_DATABRICKS.md` | Vector Search opcional |

### Ejercicios

1. Listá en `config.py` qué cambiarías para un corpus 10× más grande
   (chunk size, top-k, backend). Justificá.
2. Leé `store_factory.py`: ¿qué tendrías que implementar para un tercer
   backend? (interfaz de `VectorStore`, no “instalar pgvector”: **no
   está** en este repo).

### Criterio de salida

Ves el RAG como servicio versionable, no como notebook de Hugging Face.

---

## Módulo 9 — Experimento de cierre (integrador)

Elegí **uno**. El objetivo es el método científico, no un feature merge.

**Opción A — Chunking.** Cambiá overlap (p.ej. 64 → 32 o 128) en un
branch, re-ingerí, re-corré ablation **sobre el mismo** `qa_set.json`.
¿Hit@K se mueve? ¿Latencia de ingest?

**Opción B — Query léxica.** Agregá 5 preguntas que citen un token
exacto (un nombre de setting). Compará mentalmente vector vs hybrid
(o mirá ranks en logs). Documentá si BM25 aporta en **esa** clase.

**Opción C — Prompt.** Endurecé o relajá la regla de “no sé”. Medí
faithfulness light. Esperá ruido: n=20.

Escribí un mini-ADR (media página): contexto, cambio, métricas, qué
**no** concluyís. Eso es el skill de staff: incertidumbre explícita.

---

## Qué no entra en este plan (a propósito)

Para no diluir el foco:

- Entrenar redes desde cero, backprop, CUDA
- Fine-tuning / LoRA de LLMs
- Agentes autónomos, tool-calling complejo, multi-turno
- RAGAS full, Langfuse, streaming, caché Redis
- MLOps genérico (MLflow, feature stores) salvo el puente obvio:
  eval sets y reproducibilidad

Cuando termines los 10 módulos, esos temas se apoyan en un modelo
mental sólido. Antes, suelen ser ruido.

---

## Ruta de lectura del repo (orden sugerido)

1. `README.md`
2. `docs/ARCHITECTURE.md`
3. `app/core/pipeline.py` (mapa)
4. `chunker.py` → `embedder.py` → `vector_store.py`
5. `bm25_store.py` → `hybrid_search.py` → `reranker.py`
6. `generator.py`
7. `docs/adr/0001` … `0005` (una por módulo 3–6)
8. `docs/EVALUATION.md`
9. Tests del módulo que estés tocando

Corpus de demo (útil como “datos de negocio”): `data/sample/*.md`
incluye textos sobre Medallion, Delta, retrieval y BGE-M3. Leelos:
son a la vez **documentación indexada** y **material del dominio**.

---

## Recursos externos (pocos, alineados)

No hace falta un catálogo de 40 cursos. Con esto alcanza para
acompañar el código:

- [Reciprocal Rank Fusion (Cormack et al.)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) — el paper de `k=60`
- [BGE-M3](https://arxiv.org/abs/2402.03216) — el embedder
- [Chroma docs](https://docs.trychroma.com/) — el store local
- [Gemini API key](https://aistudio.google.com/app/apikey) — generación $0

Si más adelante querés teoría de IR: “Introduction to Information
Retrieval” (Manning) cubre TF-IDF/BM25. Si querés LLM internals: un
capítulo de tokenización + attention alcanza; no bloquea este MVP.

---

## Checklist de “ya puedo trabajar en este código”

- [ ] Expliqué RAG vs fine-tuning vs “solo LLM”
- [ ] Corrí ingest + una query + una pregunta fuera de corpus
- [ ] Sé qué es un chunk, overlap y por qué tiktoken
- [ ] Distingo embedding (bi-encoder) de rerank (cross-encoder)
- [ ] Escribí RRF a mano
- [ ] Sé dónde está el prompt y las citas `[#N]`
- [ ] Leí las métricas sin inflarlas
- [ ] Encontré el knob `ENABLE_RERANK` y el backend del vector store
- [ ] Hice un experimento con el mismo eval set

Cuando esa lista está tildada, no sos “AI engineer de marketing”:
podés **cambiar** este sistema y **medir** si lo empeoraste.
