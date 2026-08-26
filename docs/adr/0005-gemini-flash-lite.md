# ADR-005: Gemini Flash-Lite como generador (en vez de GPT-4 o Claude)

## Estado
Aceptado (2026-08-26)

## Contexto
El generador del RAG toma el top-K de chunks y produce la respuesta. Opciones evaluadas:

| Opción | Costo / 1M tokens (input) | Costo / 1M tokens (output) | Free tier |
|--------|---------------------------|---------------------------|-----------|
| **OpenAI GPT-4o-mini** | $0.15 | $0.60 | $5 credit (90 días) |
| **Anthropic Claude 3.5 Haiku** | $0.80 | $4.00 | No |
| **Gemini 2.5 Flash-Lite (alias `-latest`)** | $0.10 | $0.40 | Sí, ~15 RPM, 1M TPM, 1000+ RPD |
| **Llama 3.1 8B (local)** | $0 (costo de GPU) | $0 | Sí, limitado por hardware |

## Decisión
**Gemini Flash-Lite** (`gemini-flash-lite-latest`).

## Razones
1. **Costo cero en free tier**: el alias `-latest` siempre apunta a la versión más reciente con los límites free más generosos (Flash-Lite ~15 RPM, 1M TPM, 1000+ RPD).
2. **Calidad suficiente para RAG**: para responder preguntas sobre docs indexados, no se necesita razonamiento complejo. Flash-Lite es ~95% tan bueno como Pro en tareas de lectura.
3. **Multilingual nativo**: la documentación es bilingüe (español + inglés). Gemini maneja code-switching fluidly.
4. **Sin GPU en el cliente**: a diferencia de Llama, no requiere infra. Es HTTP.
5. **Latencia baja**: 1-2s para respuestas de 200 tokens. Aceptable para UX.

## Gotcha: modelos deprecados para new users (agosto 2026)
Al crear una API key nueva, los modelos explícitos (`gemini-2.0-flash`, `gemini-2.5-flash-lite`) devuelven **404 "no longer available to new users"**. Solo los aliases `-latest` funcionan. Esto fue una decisión de Google en 2026-Q3.

## Gotcha: `gemini-flash-latest` consume quota rápido
El alias `gemini-flash-latest` apunta al Flash "full" (no Lite). En una key free, 4-5 calls pueden agotar la quota del día (1/4 por call). Para portfolio se usa `-flash-lite-latest` por default.

## Consecuencias
- **Positivas**: cero costo operativo. 100% reproducible (mismo modelo siempre). Demo-friendly.
- **Negativas**: vendor lock-in parcial (API only). Depende de la disponibilidad de Google AI Studio.
- **Mitigación**: el `Generator` es una clase abstracta. Cambiar a OpenAI o Claude es cambiar la implementación sin tocar el resto del pipeline.

## Cuándo reconsiderar
- Si la precisión de respuestas no llega al 80% en el eval: subir a `gemini-flash-latest` o `gemini-pro-latest` (costo ~4x).
- Si el corpus excede 100K chunks y la latencia del LLM es el cuello: usar GPT-4o-mini (más rápido).
