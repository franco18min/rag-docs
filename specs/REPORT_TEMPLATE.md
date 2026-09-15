# Plantilla Informe (agentes SDD)

Copiar el bloque. No pegar archivos enteros. Código de producto en inglés; este informe en español.

```
Informe:
AGENTE: <Specify|A1|A2|A3|A4|A5|A6|A7|A8>
STATUS: pass|fail|blocked
FILES: <paths tocados, comma-separated>
AC:
  - [pass|fail] <criterio 1>
  - [pass|fail] <criterio 2>
DIFFSTAT: <pegar salida de git diff --stat>
TESTS: <comando + resumen | n/a>
GAPS: <huecos / riesgos residuales | none>
NEXT: none | retry-self
```

## Campos

| Campo | Valores |
|-------|---------|
| AGENTE | id del lote |
| STATUS | `pass` todos los AC; `fail` AC rotos; `blocked` dependencia externa |
| FILES | paths reales |
| AC | un ítem por AC de la spec; `pass`/`fail` |
| DIFFSTAT | `git diff --stat` (working tree vs HEAD) |
| TESTS | lo corrido, o `n/a` si Specify/docs-only |
| GAPS | lo que queda; no re-explicar RAG |
| NEXT | `none` si listo; `retry-self` si el mismo agente debe reintentar |
