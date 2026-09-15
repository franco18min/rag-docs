# Arquitectura Medallion

Las capas Bronze, Silver y Gold se diferencian así:

- Bronze almacena datos crudos e inmutables tal como llegan de los sistemas fuente.
- Silver contiene datos limpios, deduplicados y enriquecidos con joins y reglas de negocio.
- Gold es la capa de agregación de negocio, optimizada para consumo analítico y reporting.

## Multi-hop y fallos

El patrón multi-hop (Bronze → Silver → Gold) escala bien ante fallos porque cada capa es inmutable hacia atrás. Si una regla de negocio en Gold falla, se puede recomputar Gold desde Silver sin tocar Silver. Si Silver tiene un bug, se recomputa desde Bronze sin tocar Bronze.

Esta propiedad de re-derivación es la que hace el patrón resiliente: la inmutabilidad de Bronze y la idempotencia de las transformaciones son requisitos para que el rollback funcione.
