# Arquitectura — geaiq_mdp

> Cómo funciona el pipeline `giqmd` por dentro. Derivado de DESIGN.md + lectura del código (27 May 2026).

## Pipeline canónico

```
metadata/{país}/*.yml
  → load_data(data/*.yaml)              # anclas globales (scales, periods, attrs, groups)
  → parse_metadata(PersistentAnchorYAML) → List[Source]   (Pydantic v2)
  → get_processor(source)               # factory (type, platform) → backend gcp|airflow
  → .check(source)                      # dry-run BQ / descarga shapefile Drive
  → .deploy(source)                     # crea en GeaIQ API + carga observables/datos
  → report (plain/md/html/json)         # → GCS público + notificación Google Chat
```

## Mapa de módulos (`src/geaiq_mdp/`)

**Pipeline core**
- `giqmd.py` — entry point Click (~520 líneas). Opciones globales (`--context`, `--target`, `--root`, cache, `--debug`, `--chat-webhook`). ⚠️ tiene un bloque `pip install` interno (líneas ~63-74) frágil → BUG-03.
- `checker.py` — orquesta validación: `iter_sources(expected_status=READY)` → `processor.check()`. ⚠️ usa `report[-1]` asumiendo invariante implícita → BUG-02.
- `deployer.py` — orquesta deploy: `iter_sources(expected_status=VALID)` → `processor.deploy()`, pasando `context=load_data()`.

**Parseo / carga YAML**
- `data.py` — `load_data(root, reader)` carga `data/*.yaml` en orden alfabético. **INVARIANTE: debe correr antes que cualquier `parse_metadata()` con el MISMO reader** (sino las anclas `*ScaleX`/`*PerYYYY` no resuelven → ParseError).
- `parsers.py` — `parse_metadata()` → `List[Source]`, `parse_menu()`. ⚠️ `dump_metadata()` referencia `reader`/`filename` sin definir → BUG-01 (NameError si se llama).
- `readers.py` — `read_data()` con `TypeAdapter`; `register()` registra tags YAML custom en ruamel.
- `persistent_anchor_yaml.py` — `PersistentAnchorYAML` + `PersistentAnchorComposer`. Mantiene un **stack de anclas** entre cargas: `push_anchors()` snapshotea tras `load_data()`, se restaura antes de cada archivo de metadata. Es lo que permite `&anchors` globales reusadas en todos los YAML.
- `io_sources.py` (~239 líneas) — `iter_sources()` generador `(Source, report)`. Maneja los contextos. `docker_md_yaml()` baja un tarball del commit desde la GitHub API (requiere `GIT_TOKEN`, `METADATA_GIT_REPO`, `GIT_COMMIT`).

**Procesadores**
- `processor.py` (~1851 líneas) — clase base `Processor` + 28+ excepciones custom (`DuplicatedColumnNames`, `ObservationWithoutObservable`, `ColumnWithoutDefault`, …). Lógica de transformación: geometrías, datos, período, dimensiones, observables. Usa `@cache()` (pickle).
- `processors.py` — factory `get_processor(source)` por `(source.type, source.platform)` **+ backend** (`_detect_backend()`): elige cliente directo de Google (`gcp`) o adaptador Airflow según los providers instalados. Detalle: `docs/processors-and-backends.md`.
- `bigquery.py` — `BigQuerySourceProcessor.test_source()` dry-run + valida schema + estima costo; `run_query()` cacheable. Imports de Google lazy (requiere `[gcp]`).
- `shape.py` — `ShapeProcessor`: baja ZIP de Drive (`MediaIoBaseDownload`), detecta encoding (chardet), retorna `GeoDataFrame`. Imports lazy (requiere `[gcp]`).
- `airflow_bq.py` / `airflow_pg.py` / `airflow_shape.py` — adaptadores Airflow (a11/a12): heredan de `Processor`/`ShapeProcessor` y solo sobreescriben `setup()` para obtener el cliente vía `BigQueryHook` / `PostgresHook` / `GoogleDriveHook`. `airflow_pg.py` es la **implementación real de la fuente Postgres** (antes placeholder).
- `airflow_utils.py` — `resolve_conn_id(slug, default)` (a13): convención `mdp.{slug}` para que cada source elija su conexión Airflow (cae al default por plataforma si no existe).

**API / GCP**
- `geoecon_api.py` (~600 líneas) — cliente HTTP GeaIQ API (retry 5x backoff). Subclases por ambiente (Dev/Prod). Endpoints `wh/observables`, `wh/sources`, `wh/periods`, `wh/dimensions`, `ui/tags`. ⚠️ `update_period()` no implementado (TECH-04).
- `gcp.py` — setup ADC / credenciales BigQuery/Drive/GCS. Env: `GOOGLE_APPLICATION_CREDENTIALS`, `CHAT_WEBHOOK`, `GIT_TOKEN`, `METADATA_GIT_REPO`, `METADATA_DIR`.

**Reportes / cache / utils**
- `report.py` (~534 líneas) — formatea plain/markdown/html/json; HTML con matplotlib + MathJax.
- `cache.py` — pickle local `~/.geoecon-cache/`, decorator `@cache()`. ⚠️ sin TTL, no thread-safe, **sin versionado de schema** → falla críptica tras cambiar modelos Pydantic (TECH-01); workaround `--clean-full-cache`.
- `utils.py`, `menu.py` (DSL menú + `tags upload`), `spreadsheet.py` (`import` de Google Sheets), `google_chat.py`, `process_logger.py`, `timeout.py`, `drive.py`, `storage.py`, `unit_types.py`, `agg_op.py`, `version.py`.

## Patrón Processor + backends (gcp directo vs airflow)

Desde a11 el factory tiene **dos ejes**: el tipo de source `(type, platform)` y el **backend** según dónde
corre el CLI:

- **`gcp` / directo** — clientes de Google (`bigquery.py`, `shape.py`, `gcp.py`), requiere `geaiq_mdp[gcp]`.
  Uso: notebook, API, Cloud Run Job.
- **`airflow`** — adaptadores (`airflow_*.py`) que delegan la conexión a los Hooks de los providers
  (`apache-airflow-providers-{google,postgres}`), requiere `geaiq_mdp[airflow]`. Uso: worker del DAG.

`_detect_backend(platform)` (`processors.py:11`) prueba importar el Hook del provider; si está → `airflow`,
si no → cliente directo. Cada adaptador **solo sobreescribe `setup()`** (patrón template method: la base
`Processor` define check/deploy/transform, la subclase cambia cómo obtiene el cliente). La conexión por source
se resuelve con `mdp.{slug}` (`airflow_utils.py`). Motivo del diseño: evitar el conflicto `cryptography`
google↔Airflow (deps GCP fuera del core, lazy imports). Detalle completo: `docs/processors-and-backends.md`.

## Invariantes / gotchas (¡leer antes de tocar!)

1. **`load_data()` antes de `parse_metadata()`** con el mismo reader — sino las anclas no resuelven.
2. **Stack de anclas** (`push/pop_anchors`) — si el flujo se interrumpe entre archivos, el stack queda inconsistente.
3. **Cache pickle sin versión** — tras cambiar un modelo Pydantic, `--clean-full-cache` o errores `AttributeError` crípticos.
4. **`report[-1]` en checker.py** asume que `iter_sources` insertó el elemento antes del body (BUG-02).
5. **`ColumnRef` sin validación temprana** — referencia a columna inexistente falla recién en runtime del processor.
6. **`status: deployed` vs `done`** — ambos existen, semántica ambigua (TECH-02).

## Contextos de ejecución (`--context`)

`none` (args CLI) · `file` (lista en archivo) · `all` (todos los `metadata/**/*.yml`) · `stdin` · `commit` (modificados en el último commit git) · `docker` (baja tarball del commit vía GitHub API → `METADATA_DIR`). Mismo comando sirve local y en CI/CD.

## Deploy

`cloudbuild.yaml`: docker build → Artifact Registry → `gcloud run jobs deploy metadata`. Dockerfile python:3.11-slim, ENTRYPOINT `giqmd --context docker ...`. Ejecución vía `gcloud run jobs execute metadata --args=...` (timeout 10h, 3 retries). Targets `make check-metadata/deploy-metadata/reset-metadata file=...` lo disparan.
