# Databricks Vector Search

## Tipos de endpoint

Databricks Vector Search tiene dos tipos de endpoint: STANDARD, con latencia ~50-100ms adecuado para índices de hasta ~10M vectores por endpoint; y STORAGE_OPTIMIZED, para más de 10M vectores con latencia ~100-200ms y menor costo por vector. Los STORAGE_OPTIMIZED además soportan index_subtype='FULL_TEXT' para búsqueda solo por keyword sin embeddings.

## Pre-computed vs managed embeddings

En pre-computed embeddings tu pipeline calcula los embeddings (BGE-M3, OpenAI, etc.) y los escribe en la columna embedding, dándote control total sobre el modelo y permitiendo versionarlos. En managed embeddings el índice llama automáticamente a un modelo de Databricks Foundation Models al insertar un documento sin embedding, sin necesidad de calcularlos localmente pero atado al modelo del vendor.

Al crear un delta sync index se usan los parámetros embedding_vector_column='nombre_columna' y embedding_dimension=N. Esto le indica al índice que use los embeddings que ya están en esa columna, sin llamar al modelo de embeddings de Databricks. El pipeline es responsable de poblar la columna con los vectores correctos (por ejemplo BGE-M3 de 1024 dims).

## Modos de sincronización

Un índice delta sync de Vector Search tiene dos pipeline_type: TRIGGERED, donde la sincronización es manual llamando index.sync() y útil para batch updates; y CONTINUOUS, donde la sincronización es automática vía CDC del log de Delta, más cara pero siempre fresh, ideal cuando los datos cambian constantemente.

## Columnas de la Delta table source

La Delta table debe tener al menos: una columna primary key (STRING, INT o LONG), una columna de embeddings llamada por convención embedding con tipo ARRAY<FLOAT> y dimensión fija, y columnas adicionales que se devuelven en el resultado (text, source, metadata, etc.). El índice se monta sobre la tabla con create_delta_sync_index apuntando source_table_name al nombre fully-qualified de la tabla.
