# Estudio guiado: de data engineer a RAG

Este directorio es el curso. **Un archivo = un módulo = una sesión con
el agente (yo).** No leas los diez de una sentada: el aprendizaje es
conversado. Vos leés y hacés el laboratorio; yo explico, corrijo y no
salteo al siguiente hasta que pases el criterio de salida.

## Cómo pedirme que te guíe

En Cursor, en un chat sobre este repo, pegá **exactamente** el módulo
en el que estás. Ejemplos:

```
Estoy en el módulo 0. Guiame. Un paso a la vez. No adelantes el módulo 1.
Cuando haga una parada, esperá mi respuesta antes de continuar.
```

```
Terminamos el módulo 2. Pasemos al 3. Guiame igual: explicación, código, parada, lab.
```

```
Me trabé en el módulo 4, RRF. Explicame la fórmula con un ejemplo numérico
usando hybrid_search.py.
```

Reglas que yo debo seguir (y vos me las podés recordar):

1. Un módulo por turno de clase, salvo que pidas saltear.
2. Explicar el concepto **antes** de mandarte a leer tres archivos.
3. Usar analogías de data engineering.
4. Después de cada **parada**, esperar tu respuesta (o tus dudas).
5. No inflar métricas de este repo ni vender hybrid/rerank como “ganadores”.

Empezá acá: [`m00-por-que-rag.md`](m00-por-que-rag.md).

## Mapa DE → este sistema

| Lo que ya sabés | Acá |
|---|---|
| ETL / ingestión | Loaders + chunking |
| Schema / linaje | Metadata del chunk + Pydantic |
| Índice (Delta, Elastic) | Chroma + BM25 |
| Union de fuentes | RRF |
| Data quality tests | `qa_set.json` + Hit@K / MRR |
| Orquestador | `RAGPipeline` |
| Servicio | FastAPI |
| ADR | `docs/adr/` |

La diferencia: el output no es una tabla, es **texto**. El riesgo es
**alucinación**. RAG hace que el modelo **lea** el corpus en el query,
no que lo “recuerde”.

## Índice de módulos

| # | Archivo | Qué sale sabiendo |
|---|---|---|
| 0 | [m00-por-que-rag.md](m00-por-que-rag.md) | RAG vs solo LLM vs fine-tuning |
| 1 | [m01-correr-el-mvp.md](m01-correr-el-mvp.md) | Un request real, in-corpus y fuera |
| 2 | [m02-chunking.md](m02-chunking.md) | Tokens, 512/64, metadata |
| 3 | [m03-embeddings.md](m03-embeddings.md) | Vectores, cosine, índice offline |
| 4 | [m04-hibrido-rrf.md](m04-hibrido-rrf.md) | BM25 + RRF a mano |
| 5 | [m05-rerank.md](m05-rerank.md) | Bi-encoder vs cross-encoder, opt-in |
| 6 | [m06-generacion.md](m06-generacion.md) | Prompt, temperatura, citas `[#N]` |
| 7 | [m07-evaluacion.md](m07-evaluacion.md) | Hit@K, MRR, judge light sin marketing |
| 8 | [m08-sistema.md](m08-sistema.md) | Config, API, factory, CI |
| 9 | [m09-experimento.md](m09-experimento.md) | Un cambio medido + mini-ADR |

Tiempo: ~45–90 min por módulo. GPU no hace falta.

## Glosario (consultalo; no lo memorices)

- **LLM**: genera el siguiente token. No es una base de hechos. Acá: Gemini Flash-Lite.
- **Token**: subpalabra. `tiktoken` los cuenta.
- **Prompt**: instrucciones + pregunta + contexto (`generator.py`).
- **Embedding**: texto → vector (1024 dim con BGE-M3).
- **Coseno**: similitud por ángulo. ~1 = muy parecidos.
- **Bi-encoder**: embeddea query y doc por separado (BGE-M3).
- **Cross-encoder**: mira el par junto (reranker).
- **Retrieval / generation**: buscar chunks / redactar la respuesta.
- **Grounding**: atar claims al contexto. Citas `[#N]`.
- **Alucinación**: inventar. Faithfulness lo aproxima.
- **BM25**: ranking por palabras (tipo Elastic).
- **RRF**: `1/(k + rank)` por retriever; fusiona puestos.
- **Hit@K**: ¿el source correcto está en el top K?
- **MRR**: promedio de `1/posición` del primer acierto.
- **LLM-as-judge**: un LLM puntúa a otro. Ruidoso.

## Qué no entra (aún)

Entrenar redes, LoRA, agentes, multi-turno, Langfuse, RAGAS full,
streaming, Redis. Cuando termines el 9, esos temas se apoyan en un
modelo mental; antes son ruido.

## Checklist final

Está en el módulo 9. No tildes módulos futuros: el orden importa
porque cada pieza asume la anterior.
