# A3 — Citas ancladas

## Contexto

`Generator._format_context` arma `[Fuente: ...]` **sin** `[#N]`. El modelo no puede citar números estables. La API/UI pueden devolver citas = top-k crudo, no las mencionadas.

## Toca

- `app/core/generator.py`
- `app/models/response.py` si hace falta
- `app/main.py` (armado de citas; coordinar CORS/health con A6 **sin** hacer A6)
- `app/streamlit_app.py`

## No toca

Retrieval, eval, CI, README portfolio, Docker.

## Comportamiento

- `_format_context` imprime bloques `[#N] [Fuente: ...]` (N = 1-based, mismo orden que `context_chunks`).
- Tras generar: parsear `[#N]` en la respuesta; devolver **esas** citas (chunk N).
- Si no hay `[#N]` parseables: fallback top-k **y** log warning.
- Streamlit muestra el mismo `#N` que el contexto/API.

## AC verificables

- [ ] Cada bloque de contexto contiene `[#N]` y `[Fuente: ...]`.
- [ ] Respuesta con `[#2]` y `[#1]` → citas = chunks 2 y 1 (orden de aparición o numérico, documentado en código).
- [ ] Sin markers: citas = top-k y warning en logs.
- [ ] Streamlit: numeración idéntica a la API.
- [ ] Diff no toca retrieval/eval/CI.

## Riesgos

- Gemini ignora el formato → fallback frecuente (aceptable si se loguea).
- Off-by-one N vs índice 0.
- Duplicar lógica de parseo API vs UI (una sola función).
