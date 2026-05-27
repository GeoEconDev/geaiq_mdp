# geaiq_mdp — Context (briefing del proyecto)

> Briefing para agentes de IA y devs. Generado 27 May 2026 releyendo README/DESIGN/AGENTS/BACKLOG/CHANGELOG + código. Mantener actualizado al cambiar stack/arquitectura.

## Qué es

CLI **`giqmd`** (paquete Python `geoecon_metadata`) que **valida y despliega metadatos geoeconómicos** a la API de GeaIQ + warehouse (BigQuery / PostgreSQL). Es el **puente** entre los analistas (que escriben YAML en el repo de datos `geaiq_metadata`) y la API/warehouse de GeaIQ.

**No es** una app web ni un servicio: es un pipeline de procesamiento que corre local o como **Cloud Run Job**.

```
metadata/*.yml  →  parse (PersistentAnchorYAML + Pydantic v2)
               →  check (BigQuery dry-run / shapefile download)
               →  deploy (GeaIQ API + tablas BigQuery/Postgres)
               →  report (HTML/Markdown/JSON → GCS + Google Chat)
```

**Split 2026-05-22:** el repo se partió en dos — `geaiq_mdp` (este, CÓDIGO) y `geaiq_metadata` (DATOS YAML). CLI renombrado `gemd` → `giqmd`. Repo canónico histórico: `github.com/GeoEconDev/metadata`.

## Stack

- **Python ≥ 3.11**, Pydantic v2, Click (CLI), ruamel.yaml (anclas persistentes), GitPython.
- **GCP**: google-cloud-bigquery, google-cloud-storage, google-api-python-client (Drive), pandas-gbq, gspread, geopandas.
- **Deploy**: Dockerfile (python:3.11-slim) → Artifact Registry → **Cloud Run Job** `metadata` (proyecto `geoecon-dev`, us-central1). CI en `cloudbuild.yaml`.

## Archivos críticos (`src/geoecon_metadata/`)

| Archivo | Rol | Doc |
|---|---|---|
| `giqmd.py` | Entry point CLI (Click). Contextos, targets, cache, logging, Chat. | `docs/cli-and-workflow.md` |
| `persistent_anchor_yaml.py` | YAML con **anclas persistentes entre archivos** (magia central). | `docs/architecture.md` |
| `data.py` | `load_data()` — carga `data/*.yaml` (anclas globales). **Debe correr ANTES de parsear metadata.** | `docs/architecture.md` |
| `parsers.py` / `readers.py` | YAML → Pydantic; registro de tags custom. | `docs/architecture.md` |
| `io_sources.py` | `iter_sources()` — selección de archivos según `--context`. | `docs/architecture.md` |
| `checker.py` / `deployer.py` | Orquestan check / deploy. | `docs/architecture.md` |
| `processor.py` (1851 líneas) | Clase base `Processor` + 28+ excepciones; transformación geo/datos/dims. | `docs/architecture.md` |
| `processors.py` | Factory `get_processor()` → BigQuery / Shape (+ PostgreSQL placeholder). | `docs/architecture.md` |
| `bigquery.py` / `shape.py` | Procesadores concretos (dry-run BQ / descarga Drive). | `docs/architecture.md` |
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

5 archivos en `src/tests/` (`test_yml_anchor`, `test_yml_data`, `test_yml_parsing`, `test_report` = offline; `test_query` = requiere GCP/BigQuery). **`pytest` NO está en `pyproject.toml`** ni hay `[tool.pytest]`/conftest. Para correr: `pip install pytest && pytest src/tests/`. Cobertura insuficiente (TECH-10). Detalle en `docs/tests.md`.

## Relación con otros repos

- **`geaiq_metadata`** — los DATOS YAML que este CLI procesa (anclas `data/` + sources `metadata/{país}/`).
- **`api.geaiq.com`** — destino del deploy (warehouse + endpoints `wh/*`).
- Forma parte del ecosistema GeoEcon (ver el repo padre `geoecon_map` y su marco de abstracción de datos `design-data-abstraction.md` — este pipeline ES el "data plane" de ese diseño).

## Protocolo `.roots/`

Memoria persistente. Al iniciar sesión: leer `context.md` + `journal/diary.md` (últimas) + `journal/notes.md` + `tasks/todo.md` + `debug/errors-log.md` + `_meta.json`. Al cerrar tareas: actualizar `tasks/` + `docs/commits.md` (+ errors/fixes/decisions según aplique). Hooks en `.roots/hooks/`. Seed en `.roots/roots_seed.md`.
