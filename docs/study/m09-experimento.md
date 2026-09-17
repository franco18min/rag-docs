# Módulo 9 — Experimento de cierre

**Tiempo:** una sesión de lab + media página escrita. **Prerrequisito:** módulos 2–8.

```
Estoy en el módulo 9 (docs/study/m09-experimento.md).
Ayudame a elegir UNA hipótesis y a no sobreconcluir.
```

---

## Hoy te quiero dejar con método, no con un feature

Elegí **una** opción. El entregable no es un merge: es un mini-ADR
(contexto, cambio, métricas, qué **no** concluis).

Usá **el mismo** `data/eval/qa_set.json` para comparar antes/después.
Si cambiás el eval set a la vez, mezclás variables (como cambiar
fuente y job en el mismo deploy).

---

## Opción A — Chunking

Cambiá overlap (p.ej. 64 → 32 o 128) en un branch. Re-ingerí. Corré
ablation. ¿Hit@K se mueve? ¿Cuánto tardó el ingest?

Hipótesis ejemplo: “más overlap sube recall y baja precision / infla
el índice”.

---

## Opción B — Clase de query léxica

Agregá ~5 preguntas que citen un **token exacto** de los samples.
Compará (aunque sea a ojo o con ranks) vector vs hybrid.

Hipótesis: “BM25 aporta en esta clase; en el set original, semántico,
no se veía”.

---

## Opción C — Prompt

Endurecé o relajá la regla de “no sé”. Corré evaluate_light. Esperá
**ruido**: n=20.

Hipótesis: “un ‘no sé’ más estricto sube faithfulness y puede bajar
relevancy”.

---

## Cómo te guío yo en este módulo

1. Elegís A, B o C y me pegás la hipótesis en una frase.
2. Yo te ayudo a fijar **una** variable y el comando de medición.
3. Corrés. Me pegás números crudos.
4. Juntos redactamos el mini-ADR: especialmente la sección “qué no
   podemos afirmar”.

No implemento el experimento por vos si el objetivo es que lo sientas;
sí te desbloqueo si el script falla.

---

## Mini-ADR (plantilla)

```
# Experimento: …
Estado: one-off / no merge
Contexto: …
Cambio: (un knob o un set de 5 Q léxicas)
Métricas (mismo qa_set salvo opción B): …
Qué NO concluyo: (n, CPU, corpus demo, ruido del judge)
Cuándo lo repetiría: …
```

Eso es el skill que transfiere a producción.

---

## Checklist de todo el curso

- [ ] RAG vs fine-tuning vs solo LLM
- [ ] Ingest + query in-corpus y fuera
- [ ] Chunk, overlap, tiktoken
- [ ] Bi-encoder vs cross-encoder
- [ ] RRF a mano
- [ ] Prompt y `[#N]`
- [ ] Métricas sin inflar
- [ ] Knobs y backend
- [ ] Un experimento con incertidumbre explícita

Cuando esté tildado, podés **cambiar** este sistema y **medir** si lo
empeoraste. Eso era el objetivo, no “saber AI” en abstracto.

---

## Después del 9 (optativo)

Fine-tuning, agentes, tracing, streaming, caché. Ahora sí tienen un
sitio en el mapa. Pedime uno con: `Ya cerré el módulo 9. Quiero una
clase suelta de [tema], atada a este repo.`
