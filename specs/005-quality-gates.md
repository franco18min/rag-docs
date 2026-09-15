# A5 — Tests y CI

## Contexto

CI: `ruff format --check ... || true`; mypy `|| true`. Tests no cubren BM25 persist+collection, aislamiento hybrid, skip rerank, metadata None, format `[#N]`+parser, TestClient `/health` `/query`. BGE-M3 no debe bajarse en CI.

## Toca

- `tests/**`
- `.github/workflows/ci.yml`
- `pyproject.toml` si hace falta (ruff/mypy/pytest)

## No toca

Corpus, README narrativo, eval honesty (salvo imports de test), product pipeline salvo lo ya pedido en A2/A3 (tests **llaman** ese código).

## Tests (stubs, sin pesos BGE-M3)

- BM25 persist: save/load pickle; `query(..., collection=)` aísla colecciones.
- Hybrid isolation: collection A no mezcla hits de B.
- Rerank skip: off / `TOP_K_RERANK=0` → top-k híbrido, no `[]`.
- Metadata `None` no explota upsert/query Chroma (store stub OK).
- `_format_context` incluye `[#N]`; parser extrae N; fallback+warning.
- `TestClient`: `GET /health`; `POST /query` con pipeline/generator stub.

## CI

- `ruff check` **gate** (falla el job).
- `ruff format --check` **FALLA** el job (quitar `|| true`).
- mypy: **no** `|| true`; quitar el step **o** `continue-on-error` advisory (no gate verde falso).
- No descargar BGE-M3 (`EMBEDDING_MODEL` vacío / stubs).

## AC verificables

- [ ] Los casos de test de arriba existen y pasan en local/CI con stubs.
- [ ] `ci.yml`: format check sin `|| true`.
- [ ] mypy no usa `|| true`.
- [ ] Job no fetchea `BAAI/bge-m3`.
- [ ] `ruff check` no-zero exit rompe CI.

## Riesgos

- Format check rojo masivo al primer run (A5 corrige o formatea).
- TestClient tira de `get_pipeline()` real si no se stubbea.
