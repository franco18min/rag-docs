# Módulo 0 — Por qué RAG (y no “un chatbot”)

**Tiempo:** 30–45 min. **Código:** casi nada. **Prerrequisito:** ninguno.

Pegame esto para que te guíe en chat:

```
Estoy en el módulo 0 (docs/study/m00-por-que-rag.md).
Guiame un paso a la vez. No adelantes el módulo 1.
En cada parada esperá mi respuesta.
```

---

## Hoy te quiero dejar con una frase

> RAG recupera contexto y el LLM lo usa. El modelo no “aprende” tu corpus.

Si al final la podés decir con tus palabras y un contraejemplo, pasamos.

---

## Paso 1 — Qué es un LLM (sin deep learning)

Un **LLM** (Large Language Model) está entrenado para una sola tarea
cruda: dado un texto, **adivinar el siguiente token**. De esa mecánica
salen chat, resumen, código. No sale una garantía de verdad.

Consecuencias prácticas:

- Puede escribir algo que **suena** a documentación de Delta Lake y ser
  falso (versión inventada, flag que no existe).
- Su “memoria” es el entrenamiento público, no tu `data/sample/` ni tu
  wiki interna.
- Si le preguntás sin contexto, mezcla lo que “vio en internet” con
  improvisación. Eso se llama **alucinación** cuando afirma hechos que
  no sostienen los documentos.

No necesitás saber backprop para usar este repo. Sí necesitás desconfiar
del texto fluido.

### Analogía

Es un junior que escribe SQL precioso de memoria. A veces el JOIN es
correcto. A veces inventó una columna. Sin mirar el catálogo, no sabés.

---

## Paso 2 — Tres formas de “enseñarle” tus docs

Cuando la pregunta es sobre **tu** documentación, hay tres patrones:

| Patrón | Qué hacés | Actualizar docs | Este repo |
|---|---|---|---|
| **Solo LLM** | Preguntás al modelo desnudo | Nada: ignora tus archivos | No |
| **Fine-tuning** | Adaptás los pesos con ejemplos | Caro: reentrenar | No |
| **RAG** | Indexás docs; en el query recuperás N fragmentos y se los pasás al modelo | Re-ingerir | **Sí** |

**Fine-tuning** es como materializar un cubo enorme: cada cambio de
origen implica un job pesado. Útil para estilo o formato, malo como
única estrategia para facts que cambian.

**RAG** es **query-time join**: los hechos viven en el índice (chunks).
La pregunta trae las “filas” relevantes y el LLM las redacta.

Este proyecto es RAG de punta a punta: ingest → índice vector + BM25 →
(opcional rerank) → Gemini con citas.

---

## Paso 3 — El dibujo que tenés que interiorizar

```
Documentos  →  chunks  →  índice
                              ↑
Pregunta  →  recuperar top-k ─┘  →  LLM  →  respuesta + citas
```

Dos fases:

1. **Offline (ingest):** cortar, embeddear, indexar. Como un batch ETL.
2. **Online (query):** embeddear la pregunta, buscar vecinos, generar.

Si el ingest está mal, el query falla con prosa elegante. Por eso más
adelante evaluamos **retrieval** y **generación** por separado.

---

## Paso 4 — Lectura guiada (corta)

Abrí, en este orden, solo estas secciones:

1. `README.md` — “¿Por qué este proyecto?” y el diagrama ASCII de
   arquitectura.
2. `docs/ARCHITECTURE.md` — el mismo pipeline y el apartado
   **“Qué NO está a propósito”**.

Mientras leés, anotá tres cosas que el MVP **deliberadamente no hace**
(memoria conversacional, Langfuse, RAGAS full, streaming, etc.).

No leas todavía `chunker.py`. Eso es el módulo 2.

---

## Parada 0 — Respondeme esto (antes del laboratorio)

Escribime (en el chat o en un scratch) respuestas cortas:

1. Si mañana cambia un markdown de `data/sample/`, ¿qué tenés que hacer
   en RAG vs en fine-tuning?
2. ¿Por qué “el modelo es muy bueno” no alcanza para docs internas?
3. Completá: el riesgo de DE suele ser datos sucios; el riesgo de RAG
   es ________.

Si alguna la trabás, preguntame. No pases al lab con las tres en blanco.

---

## Laboratorio 0

Sin instalar nada todavía:

1. Abrí `app/core/pipeline.py` y mirá **solo** los nombres de métodos
   `ingest` y `query` (no hace falta entender cada línea).
2. En `query`, contá los comentarios numerados (`1. Embed` … `5. Format
   citations`). Esa lista **es** el dibujo del paso 3.

Decime cuántos pasos numerados viste en `query`. Si coincidimos, el mapa
mental ya está enganchado al código.

---

## Criterio para pasar al módulo 1

- [ ] Dijiste la frase de RAG con tus palabras.
- [ ] Distinguís los tres patrones y cuál es este repo.
- [ ] Sabés que ingest es batch y query es online.
- [ ] Listaste al menos dos “no está a propósito” del Architecture.

Cuando esté, pegame:

```
Cierre módulo 0: [tus respuestas de la parada].
Listo para el módulo 1.
```
