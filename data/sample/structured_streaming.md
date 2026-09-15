# Structured Streaming

Structured Streaming ofrece un modelo de programación basado en DataFrames/Datasets, exactamente igual al batch, lo que reduce código duplicado. Tiene mejor manejo de late data con watermarks, garantías exactly-once end-to-end cuando se combina con sinks idempotentes, y el optimizador Catalyst aplica mejoras automáticamente. Estas son ventajas frente al streaming tradicional con DStreams.

## Modo continuous

El modo continuous de Structured Streaming (en beta desde Spark 2.3) apunta a latencias de ~1ms, mucho menor que los micro-batches típicos de ~100ms. Solo soporta un subconjunto de operaciones. Es útil para casos como detección de fraude en tiempo real donde los micro-batches no son suficientemente rápidos. Se activa con trigger(continuous='1 second') en el writeStream.
