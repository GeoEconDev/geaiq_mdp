# Processors y backends (registry + adapters)

> Introducido en v0.1.0a11–a13 (2026-06-05). Cómo `giqmd` elige con qué cliente correr cada source.
> Código: `processors.py`, `airflow_bq.py`, `airflow_pg.py`, `airflow_shape.py`, `airflow_utils.py`.

## Por qué existe

Las deps de Google (BigQuery, Drive, Storage, gspread, geopandas, pandas-gbq) arrastran una versión de
`cryptography` que **conflictúa** con la del entorno Airflow donde corre el DAG `metadata_processor`
(incidente 2026-06-05). La solución: que `geaiq_mdp` se instale sin esas deps y **delegue las conexiones a
los Hooks de los providers de Airflow** cuando corre dentro de Airflow, o use los clientes directos de Google
cuando corre en notebook/API/Cloud Run.

## Extras de instalación (`pyproject.toml`)

Las deps GCP ya **no** están en `dependencies`; viven en `[project.optional-dependencies]`:

| Instalación | Trae | Uso |
|---|---|---|
| `pip install geaiq_mdp` | solo core (ruamel, pydantic, click, …) | base; no arrastra google→cryptography |
| `pip install geaiq_mdp[gcp]` | geopandas, pandas-gbq, google-api-python-client, google-cloud-bigquery, google-cloud-storage, google-auth, gspread | clientes directos (notebook/API/Cloud Run) |
| `pip install geaiq_mdp[airflow]` | apache-airflow-providers-google, apache-airflow-providers-postgres | adaptadores via Hooks (worker Airflow) |
| `pip install geaiq_mdp[test]` | pytest, pandas | tests |

En el worker Airflow, los providers ya vienen instalados, así que se instala `geaiq_mdp` "pelado"
(`git+https://github.com/GeoEconDev/geaiq_mdp.git`) y los Hooks resuelven todo.

## Lazy imports

`gcp.py`, `bigquery.py`, `shape.py` hacen los imports de `google.*` / `gspread` / `googleapiclient` /
`pandas_gbq` / `geopandas` **lazy** (dentro de cada función), no a nivel de módulo. Así los módulos se importan
sin Google instalado, y `processors.py` puede decidir el backend antes de tocar ninguna dep pesada.

## Registry — `get_processor(source)` (`processors.py:33`)

Selecciona por la tupla `(source.source.type, source.source.platform)` y, dentro de cada caso, por el backend
que devuelve `_detect_backend(platform)`. Todos los imports de los processors concretos son lazy.

| type / platform | backend `airflow` | backend `gcp` / directo |
|---|---|---|
| `sql` / `bigquery` | `AirflowBigQueryProcessor(slug=…)` | `BigQuerySourceProcessor()` |
| `sql` / `postgresql` | `AirflowPostgreSQLProcessor(slug=…)` | ❌ `NotImplementedError` (no hay cliente directo Postgres) |
| `shape` / `googledrive` | `AirflowShapeProcessor(slug=…)` | `ShapeProcessor()` |
| otro | — | `ValueError` (sin processor) |

`source_type_processors` quedó como `None`; el dict legacy se obtiene con `_lazy_source_type_processors()`
(solo si `geaiq_mdp[gcp]` está instalado).

## Auto-detección de backend — `_detect_backend(platform)` (`processors.py:11`)

Intenta importar el Hook del provider correspondiente; si lo encuentra → `"airflow"`, si no → cliente directo:

| platform | prueba importar | hay provider | no hay provider |
|---|---|---|---|
| `bigquery` | `airflow.providers.google.cloud.hooks.bigquery` | `airflow` | `gcp` |
| `postgresql` | `airflow.providers.postgres.hooks.postgres` | `airflow` | `direct` (no implementado → error en el registry) |
| `googledrive` | `airflow.providers.google.suite.hooks.drive` | `airflow` | `gcp` |

## Adaptadores Airflow

Todos heredan de `Processor` (o de un processor concreto) y **solo sobreescriben `setup()`** para obtener el
cliente vía Hook; toda la lógica de check/deploy/transformación se reutiliza de la clase base.

- **`AirflowBigQueryProcessor`** (`airflow_bq.py:10`): en `setup()` instancia `BigQueryHook(gcp_conn_id=…)`,
  obtiene `client_bq` y `project_id`. `run_query()` usa `hook.get_pandas_df()`; `test_source()` hace dry-run
  con `QueryJobConfig(dry_run=True)` y arma el reporte de costo/schema/`exists_shape_id` igual que el directo.
- **`AirflowPostgreSQLProcessor`** (`airflow_pg.py:10`): en `setup()` instancia `PostgresHook(postgres_conn_id=…)`.
  `run_query()` usa `hook.get_pandas_df()`; `test_source()` corre `EXPLAIN <query>` como dry-run (cost/total = 0,
  `exists_shape_id=True`, plan en `description`). **Esto es la implementación de la fuente Postgres** que antes
  era un `NotImplementedError` placeholder.
- **`AirflowShapeProcessor`** (`airflow_shape.py:5`): hereda de `ShapeProcessor` y solo cambia `setup()` para
  obtener `drive_service` vía `GoogleDriveHook.get_conn()` en lugar de `setup_drive()`. Salta el `setup()` del
  padre llamando directo a `Processor.setup(self, …)`. La descarga de ZIP y el parseo de shapefiles se reusan.

## Conexión por slug — `mdp.{slug}` (`airflow_utils.py:5`)

`resolve_conn_id(slug, default)` decide qué conexión Airflow usa cada source:

1. Arma `mdp.{slug}` e intenta `Connection.get_connection_from_secrets("mdp.{slug}")` (esto también resuelve
   la env var `AIRFLOW_CONN_MDP_{SLUG}`).
2. Si existe → usa `mdp.{slug}`.
3. Si lanza excepción → devuelve `default` (`google_cloud_default` o `postgres_default`).

Cada adaptador recibe `slug=source.slug` desde `get_processor()` y llama a `resolve_conn_id()` en `setup()`.
**Convención de operación:** para apuntar una source a una base/proyecto distinto, crear en Airflow una
conexión llamada exactamente `mdp.{slug}`; sin ella se usa la conexión default de la plataforma.
