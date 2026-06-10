# geaiq_mdp — Context (briefing del proyecto)

> Briefing para agentes de IA y devs. Generado 27 May 2026 releyendo README/DESIGN/AGENTS/BACKLOG/CHANGELOG + código; actualizado 9 Jun 2026 (releases a11–a16). Mantener actualizado al cambiar stack/arquitectura.
>
> **Versión actual: `0.1.0a16`** (`version.py` ahora lee `importlib.metadata.version()`, ya no hardcodeada — a16).

## Qué es

CLI **`giqmd`** (paquete Python `geaiq_mdp`) que **valida y despliega metadatos geoeconómicos** a la API de GeaIQ + warehouse (BigQuery / PostgreSQL). Es el **puente** entre los analistas (que escriben YAML en el repo de datos `geaiq_metadata`) y la API/warehouse de GeaIQ.

**No es** una app web ni un servicio: es un pipeline de procesamiento que corre local o como **Cloud Run Job**.

```
metadata/*.yml  →  parse (PersistentAnchorYAML + Pydantic v2)
               →  check (BigQuery dry-run / shapefile download)
               →  deploy (GeaIQ API + tablas BigQuery/Postgres)
               →  report (HTML/Markdown/JSON → GCS + Google Chat)
```

**Split 2026-05-22:** el repo se partió en dos — `geaiq_mdp` (este, CÓDIGO) y `geaiq_metadata` (DATOS YAML). CLI renombrado `gemd` → `giqmd`. Repo canónico histórico: `github.com/GeoEconDev/metadata`.

## Stack

- **Python ≥ 3.11**, Pydantic v2, Click (CLI), ruamel.yaml (anclas persistentes), GitPython. (core, sin GCP)
- **Extras** (a11): `geaiq_mdp[gcp]` = clientes directos de Google (bigquery, storage, api-python-client/Drive, pandas-gbq, gspread, geopandas) · `geaiq_mdp[airflow]` = providers Airflow (google, postgres) · `[test]` = pytest, pandas. Las deps GCP salieron de `dependencies` para evitar el conflicto `cryptography` en Airflow.
- **Backends** (a11–a13): el CLI corre con clientes directos (`gcp`) o adaptadores Airflow (`airflow_bq/pg/shape.py`, via Hooks) según `_detect_backend()`. Conexión por source: `mdp.{slug}`. Ver `docs/processors-and-backends.md`.
- **Deploy**: Dockerfile (python:3.11-slim) → Artifact Registry → **Cloud Run Job** `metadata` (proyecto `geoecon-dev`, us-central1). CI en `cloudbuild.yaml`. También se instala en el worker Airflow del DAG `metadata_processor`.

## Archivos críticos (`src/geaiq_mdp/`)

| Archivo | Rol | Doc |
|---|---|---|
| `giqmd.py` | Entry point CLI (Click). Contextos, targets, cache, logging, Chat. | `docs/cli-and-workflow.md` |
| `persistent_anchor_yaml.py` | YAML con **anclas persistentes entre archivos** (magia central). | `docs/architecture.md` |
| `data.py` | `load_data()` — carga `data/*.yaml` (anclas globales). **Debe correr ANTES de parsear metadata.** | `docs/architecture.md` |
| `parsers.py` / `readers.py` | YAML → Pydantic; registro de tags custom. | `docs/architecture.md` |
| `io_sources.py` | `iter_sources()` — selección de archivos según `--context`. | `docs/architecture.md` |
| `checker.py` / `deployer.py` | Orquestan check / deploy. | `docs/architecture.md` |
| `processor.py` (1851 líneas) | Clase base `Processor` + 28+ excepciones; transformación geo/datos/dims. | `docs/architecture.md` |
| `processors.py` | Factory `get_processor()` por `(type, platform)` + `_detect_backend()` (gcp/airflow). | `docs/processors-and-backends.md` |
| `bigquery.py` / `shape.py` | Procesadores directos GCP (dry-run BQ / descarga Drive). Requieren `[gcp]`. | `docs/processors-and-backends.md` |
| `airflow_bq.py` / `airflow_pg.py` / `airflow_shape.py` / `airflow_utils.py` | Adaptadores Airflow (Hooks) + `resolve_conn_id` (`mdp.{slug}`). Requieren `[airflow]`. | `docs/processors-and-backends.md` |
| `geoecon_api.py` | Cliente HTTP de la GeaIQ API (`wh/*`, `ui/tags`). | `docs/architecture.md` |
| `models/*.py` | Modelos Pydantic (Source, Column, Dimension, wh, menu). | `docs/models-yaml-schema.md` |
| `enums.py` | SourceType/Platform/Status, ReliabilityType, **MeasurementUnit**, ObservableScale(Type)Enum. | `docs/models-yaml-schema.md` |

## Convenciones

- **Idioma:** español para contenido/docs; inglés para código. (Hay mezcla es/en en logs — deuda TECH-07.)
- **Slug:** `{iso3}{año}-{concepto}-{escala}` (ej. `arg2023-prestamos-adm01`).
- **Branches:** `develop` (integración) + una rama por colaborador (`cr`/`jp`/`jm`/`vs`/`na`/`fc`), sincronizadas con `make sync`. NO PRs.
- **Lifecycle de una source:** `draft → ready → (check) → valid → (deploy) → deployed/done` (o `error`/`failed`). Solo el analista avanza el estado; el tooling solo retrocede a error/failed.
- **`typo`** en modelos = "tipo" (NO error tipográfico). Deuda TECH-05.

## Tests

5 archivos en `src/tests/` (`test_yml_anchor`, `test_yml_data`, `test_yml_parsing`, `test_report` = offline; `test_query` = requiere GCP/BigQuery, marcado `@pytest.mark.skip`). **Migrados a pytest (a15):** extra `[test]` (pytest, pandas) + `[tool.pytest.ini_options]` (`testpaths=["src/tests"]`, `pythonpath=["src"]`) en `pyproject.toml`, descubrimiento en VS Code. Correr: `pip install -e .[test] && pytest`. Detalle en `docs/tests.md`.

## Relación con otros repos

- **`geaiq_metadata`** — los DATOS YAML que este CLI procesa (anclas `data/` + sources `metadata/{país}/`).
- **`api.geaiq.com`** — destino del deploy (warehouse + endpoints `wh/*`).
- Forma parte del ecosistema GeoEcon (ver el repo padre `geoecon_map` y su marco de abstracción de datos `design-data-abstraction.md` — este pipeline ES el "data plane" de ese diseño).

## Protocolo `.roots/`

Memoria persistente. Al iniciar sesión: leer `context.md` + `journal/diary.md` (últimas) + `journal/notes.md` + `tasks/todo.md` + `debug/errors-log.md` + `_meta.json`. Al cerrar tareas: actualizar `tasks/` + `docs/commits.md` (+ errors/fixes/decisions según aplique). Hooks en `.roots/hooks/`. Seed en `.roots/roots_seed.md`.
