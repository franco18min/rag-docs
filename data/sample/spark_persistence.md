# Persistencia en Spark: cache() vs persist()

cache() usa el nivel de storage MEMORY_AND_DISK por defecto y es un alias de persist(). persist() te permite elegir el StorageLevel explícitamente (MEMORY_ONLY, DISK_ONLY, MEMORY_AND_DISK_2, etc.). Conviene persistir con replicación cuando el recompute es caro, y usar MEMORY_ONLY solo si el dataset entra cómodo en RAM.

## Spark UI: métricas de cache/persist

La Spark UI (puerto 4040 del driver) tiene una pestaña Storage que muestra cuánta memoria y disco ocupa cada RDD/DataFrame cacheado, qué fracción está en memoria vs disco, y el hit ratio y miss count. Si ves mucha fracción spilleada a disco probablemente estás sin RAM suficiente; soluciones son aumentar memoria del executor o particionar mejor el dataset.
