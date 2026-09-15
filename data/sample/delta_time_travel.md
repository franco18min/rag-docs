# Time Travel en Delta Lake

Time Travel permite consultar o restaurar versiones anteriores de una tabla Delta usando el VERSION AS OF o TIMESTAMP AS OF en SQL. Internamente Delta mantiene un _delta_log con commits JSON, lo que habilita auditoría, reproducibilidad de experimentos y recuperación ante cargas erróneas.

## VACUUM

VACUUM elimina físicamente los archivos Parquet que ya no están referenciados por el _delta_log y que tienen más de N horas de antigüedad (default 7 días). Pasado ese plazo el time travel no puede acceder a esas versiones porque los archivos ya no existen. Por eso se suele aumentar la retención a 30 días en data warehouse de producción, asumiendo mayor costo de storage.

## RESTORE vs SELECT VERSION AS OF

RESTORE TABLE events TO VERSION AS OF 3 sobrescribe la tabla actual con el estado de la versión 3, haciendo internamente un MERGE que añade los archivos de la versión vieja y remueve los nuevos. Es un write operation. En cambio, SELECT FROM events VERSION AS OF 3 solo lee la versión histórica sin modificar nada. RESTORE es la forma rápida de hacer rollback sin copiar Parquet manualmente.
