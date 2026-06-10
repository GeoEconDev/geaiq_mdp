# CLI `giqmd` + flujo de trabajo

> Referencia operativa. Ver `architecture.md` para el interno.

## Instalación

```bash
pip install -e .            # Python ≥ 3.11
# o solo deps: pip install -r requirements.txt
```

## Config GCP (una vez)

```bash
gcloud config set project geoecon-dev
gcloud services enable sheets.googleapis.com drive.googleapis.com bigquery.googleapis.com
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/bigquery
```

Env vars: `GOOGLE_APPLICATION_CREDENTIALS` (JSON service account, alt a ADC) · `CHAT_WEBHOOK` (Google Chat) · `GIT_TOKEN` + `METADATA_GIT_REPO` + `GIT_COMMIT` (solo `--context docker`) · `METADATA_DIR` (raíz, default `.`).

## Lifecycle de una source

```
draft → ready → (giqmd check) → valid → (giqmd deploy) → deployed/done
                                                       ↘ error / failed
```
1. Crear `metadata/{país}/{slug}.yml` con `status: draft`.
2. Completar campos → `status: ready`.
3. `giqmd check <archivo>` → si pasa, poner `status: valid`.
4. `giqmd --target dev deploy <archivo>` → `deployed`. Repetir con `--target prod`.

## Opciones globales

```
--context [none|file|all|stdin|commit|docker]   selección de archivos (default none)
--root PATH                                      raíz del repo (default .)
--target [dev|prod|test|local]                   entorno destino (default dev)
--commit TEXT                                    ref git (con --context docker)
--clean-full-cache | --invalid-cache             cache ~/.geoecon-cache/
--upload-output                                  sube reporte a Drive/GCS
--debug                                          logging DEBUG
--chat-webhook URL                               webhook Google Chat
```

## Comandos

| Comando | Descripción |
|---|---|
| `init [--update]` | Inicializa datos base (scales, periods, attributes) en la API. 1 vez por entorno. |
| `check` | Valida archivos `ready` (dry-run BQ / descarga shape). `--format html\|md\|json`, `--output FILE`, `--only-new`. |
| `deploy` | Despliega sources `valid` a la API + warehouse. Mismas flags de formato. |
| `reset FILES` | Limpia caché, logs y shapefiles de las fuentes. |
| `import SPREADSHEET_ID` | Importa metadatos desde Google Sheets. |
| `menu check` | Valida archivos de menú. |
| `tags upload` | Sube tags del menú a la API (`ui/tags`). |

### Ejemplos

```bash
giqmd check metadata/argentina/arg2023-prestamos-adm01.yml
giqmd --context commit check                        # archivos modificados en el último commit
giqmd --target dev deploy --format html --output report.html metadata/argentina/mi_fuente.yml
giqmd --target prod deploy metadata/argentina/mi_fuente.yml
giqmd reset metadata/argentina/mi_fuente.yml
giqmd --target dev init                             # solo 1 vez por entorno
```

## Makefile

| Target | Acción |
|---|---|
| `make sync` | Sincronización bidireccional develop ↔ ramas de colaboradores. |
| `make sync-from-develop` / `make sync-develop` | Un sentido cada uno. |
| `make clean-cache` / `clean-reports` / `clean-logs` | Limpieza local. |
| `make show-status` | `grep -r "status:" metadata/` (vive en el repo de datos). |
| `make check-metadata file=...` / `deploy-metadata file=...` / `reset-metadata file=...` | Ejecuta el comando en **Cloud Run Job** `metadata` (geoecon-dev, us-central1). |

## Branches

`develop` (integración) + 1 rama por colaborador: `cr` (Cristian Rocha), `jp`, `jm`, `vs`, `na`, `fc`. Merge sin PR, automatizado con `make sync`. (Evita conflictos YAML entre analistas que tocan distintos países.)

## Processors y backends (v0.1.0a11–a13, 2026-06-05)

> Doc dedicado: `docs/processors-and-backends.md` (registry, adapters, extras). Resumen operativo acá.

`get_processor(source)` (`processors.py`) elige el processor por `(type, platform)` y **auto-detecta backend**
(`_detect_backend`): si los providers de Airflow están instalados, usa los adaptadores de Airflow; si no, los
clientes directos de Google (`geaiq_mdp[gcp]`).

| type / platform | backend `airflow` (en el stack) | backend directo |
|---|---|---|
| sql / bigquery | `AirflowBigQueryProcessor` (`airflow_bq.py`, `BigQueryHook`) | `BigQuerySourceProcessor` (`bigquery.py`, requiere `[gcp]`) |
| sql / postgresql | `AirflowPostgreSQLProcessor` (`airflow_pg.py`, `PostgresHook`) | ❌ `NotImplementedError` (sin cliente directo) |
| shape / googledrive | `AirflowShapeProcessor` (`airflow_shape.py`, `GoogleDriveHook`) (a12) | `ShapeProcessor` (`shape.py`, requiere `[gcp]`) |

- **Lazy imports + extras:** las deps GCP (bigquery/drive/storage/gspread/geopandas/pandas-gbq) pasaron a
  `[project.optional-dependencies]` (extras `gcp` y `airflow`) e imports lazy. Motivo: evitar el conflicto de
  `cryptography` al instalar en el entorno Airflow (incidente 2026-06-05). `pip install geaiq_mdp` ya no
  arrastra google→cryptography; `pip install geaiq_mdp[gcp]` mantiene los clientes directos, `[airflow]` los
  providers de Airflow.

### Conexión por slug — convención `mdp.{slug}` (a13)

Cada adaptador Airflow recibe `slug=source.slug` desde `get_processor()` y, en su `setup()`, resuelve la
conexión vía `resolve_conn_id(slug, default)` (`airflow_utils.py:5`):

1. Si existe una conexión Airflow `mdp.{slug}` (`Connection.get_connection_from_secrets("mdp.{slug}")`,
   que también cubre la env var `AIRFLOW_CONN_MDP_{SLUG}`), se usa **esa**.
2. Si no, cae al default por plataforma: `google_cloud_default` (BigQuery/Drive) o `postgres_default` (Postgres).

Así un source elige su conexión postgres/bq sin tocar código: basta crear `mdp.{slug}` en Airflow. Esto cierra
el gap "cómo elige un source su conexión" (antes pendiente para Postgres).

## Exit codes — `ExitCode` enum (a14)

`giqmd` mapea el peor tipo de mensaje del reporte a un código de salida vía `ExitCode(int, Enum)`
(`enums.py:347`), que **reemplazó** al dict local `EXIT_MAP` de `giqmd.py`:

| miembro | valor | significado |
|---|---|---|
| `info` / `ok` | 0 | sin problemas |
| `warning` | 1 | advertencias |
| `error` | 2 | errores |

`worst_report_type()` (`giqmd.py:259`) toma `max(..., key=lambda a: ExitCode[a])` y `cli` hace `ctx.exit()`
con ese código. Moverlo a `enums.py` (módulo liviano) permite que el DAG de Airflow importe `ExitCode` sin
arrastrar el import de `gspread` que vivía en `giqmd.py`.
