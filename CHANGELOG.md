# CHANGELOG

Historial de cambios del proyecto geaiq_mdp.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## 2026-06-05 — v0.1.0a13: Resolución de conexiones Airflow por slug (mdp.{slug})

**Resumen:** Los adaptadores Airflow ahora intentan usar una conexión específica por fuente antes de caer al default de plataforma. La convención es `mdp.{slug}` — si esa conexión existe en Airflow, se usa; si no, se usa `google_cloud_default` o `postgres_default`.

### Cambios

- **`airflow_utils.py`** (nuevo): función `resolve_conn_id(slug, default)` — busca `mdp.{slug}` via `Connection.get_connection_from_secrets()` (también cubre env vars `AIRFLOW_CONN_MDP_*`), retorna el default si no existe.
- **`airflow_bq.py`**, **`airflow_pg.py`**, **`airflow_shape.py`**: aceptan `slug` en el constructor y llaman a `resolve_conn_id()` en `setup()`.
- **`processors.py`**: pasa `slug=source.slug` al construir cada adaptador Airflow.

---

## 2026-06-05 — v0.1.0a12: AirflowShapeProcessor para fuentes Google Drive

**Resumen:** Completa el soporte Airflow para todos los tipos de fuente. `ShapeProcessor` (Google Drive) ahora tiene su adaptador Airflow usando `GoogleDriveHook`.

### Cambios

- **`airflow_shape.py`** (nuevo): `AirflowShapeProcessor` hereda de `ShapeProcessor` y sobreescribe solo `setup()` para obtener el servicio de Drive vía `GoogleDriveHook.get_conn()` en lugar de `setup_drive()`. Toda la lógica de descarga y parseo de shapefiles se reutiliza.
- **`processors.py`**: `_detect_backend()` detecta `GOOGLEDRIVE` → `airflow` si `airflow.providers.google.suite.hooks.drive` está disponible. `get_processor()` retorna `AirflowShapeProcessor` en ese caso.

---

## 2026-06-05 — v0.1.0a11: Lazy imports y adaptador Airflow para conectores GCP

**Resumen:** Las dependencias de Google (BigQuery, Drive, Storage, gspread, geopandas, pandas-gbq) causaban conflictos de `cryptography` al instalar `geaiq_mdp` en un entorno Airflow. Se refactorizan los imports a lazy y se introduce un sistema de adaptadores con auto-detección de backend.

### Cambios

- **`pyproject.toml`**: dependencias GCP movidas de `dependencies` a `[project.optional-dependencies]`. Nuevos extras: `gcp` (clientes directos de Google) y `airflow` (providers de Airflow). Versión bumpeada a `0.1.0a11`.
- **`gcp.py`**: todos los imports de `google.*`, `gspread`, `googleapiclient` y `pandas_gbq` son ahora lazy dentro de cada función. El módulo se puede importar sin Google instalado.
- **`bigquery.py`**: imports de `pandas_gbq` y `google.api_core.exceptions` movidos a lazy dentro de `run_query` y `test_source`.
- **`shape.py`**: imports de `googleapiclient` y `geopandas` movidos a lazy dentro de `download_file` y `run_query`.
- **`processors.py`**: `get_processor()` refactorizado con imports lazy de los procesadores. Nueva función `_detect_backend(platform)` que auto-detecta si los Airflow providers están disponibles (`airflow` backend) o si usar los clientes directos de Google (`gcp` backend).
- **`airflow_bq.py`** (nuevo): `AirflowBigQueryProcessor` — adaptador que usa `BigQueryHook` de `apache-airflow-providers-google`. Compatible con la interfaz `Processor` existente; sin conflictos de dependencias en entornos Airflow.

### Comportamiento

- `pip install geaiq_mdp` en un entorno Airflow → auto-detecta hooks, sin conflicto de `cryptography`.
- `pip install geaiq_mdp[gcp]` en notebooks/API → usa clientes directos de Google como antes.

---

## 2026-06-02 — v0.1.0a10: Autenticación Bearer en `GeoEconAPI`

**Resumen:** El cliente `GeoEconAPI` no enviaba credenciales al hacer requests, causando errores 403 "Not authenticated" en endpoints protegidos (como `POST /r/{step}/{status}` para subir reportes). Se agrega soporte de autenticación vía variable de entorno.

### Cambios

- **`geoecon_api.py`**: `GeoEconAPI.__init__` ahora configura `Authorization: Bearer` en la sesión. Lee `GEAIQ_API_TOKEN` directamente si está disponible; de lo contrario, hace login con `GEAIQ_API_USER` + `GEAIQ_API_PASSWORD` contra `POST /auth/token`. Sin credenciales la sesión queda sin auth (comportamiento anterior).
- **`version.py`**: serial incrementado a `10` → versión `0.1.0a10`.

---

## 2026-06-02 — v0.1.0a9: Fix UTF-8 BOM en `pyproject.toml`

**Resumen:** `pyproject.toml` tenía un UTF-8 BOM (`EF BB BF`) al inicio del archivo. Esto causaba que `tomllib.loads()` fallara con `TOMLDecodeError: Invalid statement (at line 1, column 1)` al intentar instalar el paquete con pip, bloqueando el deploy automático en Airflow.

### Cambios

- **`pyproject.toml`**: eliminado el UTF-8 BOM; versión sincronizada a `0.1.0a9`.
- **`version.py`**: serial incrementado a `9` → versión `0.1.0a9`.

---

## 2026-05-30 — v0.1.0a8: Renombrado del paquete a `geaiq_mdp`

**Resumen:** El paquete Python se llamaba `geoecon_metadata` (nombre de distribución e importación). Se renombra a `geaiq_mdp` para que coincida con el nombre del repositorio. Se actualizan todos los imports internos, `pyproject.toml`, Dockerfile, Makefile, tests y documentación.

### Cambios

- **`src/geoecon_metadata/`** → **`src/geaiq_mdp/`**: directorio renombrado.
- **`pyproject.toml`**: `name = "geaiq_mdp"`, entry points actualizados (`geaiq_mdp.giqmd:cli`).
- Todos los `from geoecon_metadata import` / `import geoecon_metadata` reemplazados por `geaiq_mdp` en 34 archivos.
- **`version.py`**: Serial incrementado a `8` → versión `0.1.0a8`.

---

## 2026-05-30 — v0.1.0a7: `GeoEconAPIProd` también lee `GEAIQ_API_URL`

**Resumen:** `GeoEconAPIProd` tenía hardcodeada `https://api.geoecon.info/`. Como ahora hay un único servidor (`https://api.geaiq.com`) que atiende todos los ambientes, tanto DEV como PROD leen `GEAIQ_API_URL` con el mismo fallback. El flag `--target` controla el ambiente de datos dentro de la API, no el servidor.

### Cambios

- **`geoecon_api.py`**: `GeoEconAPIProd.static_uri` ahora lee `GEAIQ_API_URL` igual que `GeoEconAPIDev`.
- **`version.py`**: Serial incrementado a `7` → versión `0.1.0a7`.

---

## 2026-05-30 — v0.1.0a6: URL de API configurable via `GEAIQ_API_URL`

**Resumen:** La URL de la GeaIQ API estaba hardcodeada apuntando a la instancia antigua de Google Cloud Run (`geoecon-api-dev-...us-central1.run.app`), que ya no está disponible. Se migra `GeoEconAPIDev` y `menu.py` para leer la URL desde la variable de entorno `GEAIQ_API_URL`, con fallback a `https://api.geaiq.com`.

### Cambios

- **`geoecon_api.py`**: `GeoEconAPIDev.static_uri` ahora se obtiene de `os.environ.get("GEAIQ_API_URL", "https://api.geaiq.com/")`.
- **`menu.py`**: `geoecon_api_url` ahora se obtiene de `os.environ.get("GEAIQ_API_URL", "https://api.geaiq.com")`.
- **`version.py`**: Serial incrementado a `6` → versión `0.1.0a6`.

---

## 2026-05-22 — Se agrega CHANGELOG

**Prompt:**
> "Agrega un CHANGELOG a todos los repositorios del workspace GEAIQ: geaiq-data-stack, geaiq_airflow_dag, geaiq_api, geaiq_metadata, geaiq_mdp. Deja una primera anotación indicando que se agregó el CHANGELOG, y luego otra anotación con los cambios que se hicieron para este requerimiento."

**Resumen:** Se establece este archivo de historial de cambios para el procesador de metadata GeaIQ.

---

## 2026-05-22 — Flujo de validación y deploy de metadata para Responsables de Datos

**Prompt:**
> "Necesitamos cerrar el flujo para los responsables de datos. Los responsables de datos (RD) es un rol que tiene la responsabilidad de subir datos a la base de datos de la GeaIQ API y garantizar la calidad de esos datos. Para ello usan GeaIQ MDP que es una librería que procesa los archivos YAML cuyo DSL (GeaIQ DSL) permite identificar las fuentes de datos [...] Entonces los RD escriben los MD en la UI de la API, luego envían a validar el archivo y una vez que están validados, se puede deployar, o incluso revertir los cambios. Todo esto usando la herramienta giqmd. Pero eso ahora ocurre todo en la UI de la API."

**Resumen:** Se integra `giqmd` como herramienta de validación y deploy dentro del flujo de Airflow. El comando `giqmd --context docker --commit <sha>` descarga el tarball del commit desde GitHub y ejecuta `check`, `deploy` o `reset` sin necesidad de Google Cloud Run. El resultado se sube a la GeaIQ API vía `--upload-output`.

### Cambios

**Utilizado por el nuevo DAG `metadata_processor`**
- `giqmd --context docker`: descarga el tarball del commit indicado desde la GitHub API (requiere `GIT_TOKEN` y `METADATA_GIT_REPO`), sin depender de Cloud Run.
- `giqmd --upload-output`: sube el reporte HTML generado a `POST /api/v1/r/{step}/{status}` en la GeaIQ API.
- Flags combinados: `--context docker --commit <sha> --upload-output <operation> --format html --output report.<slug>.<op>.<target>.html <file_path>`

**Instalación en Airflow**
- El paquete se instala directamente desde GitHub: `git+https://github.com/GeoEconDev/geaiq_mdp.git` (no PyPI).

**Variables de entorno requeridas en el worker de Airflow**

| Variable | Descripción |
|---|---|
| `GIT_TOKEN` | GitHub PAT para descargar el tarball del commit |
| `METADATA_GIT_REPO` | URL de la API de GitHub del repo de metadata |
| `GEAIQ_API_URL` | URL base de la GeaIQ API (para subir reportes) |
| `GEAIQ_API_TOKEN` | Token de autenticación de la GeaIQ API |

---

## [Unreleased]

### Por hacer
- Resolver bug en `parsers.py::dump_metadata` (variables `reader` y `filename` no definidas en scope).
- Agregar `.env.example` con todas las variables de entorno requeridas.
- Completar implementación de `update_period` en el cliente API.
- Aumentar cobertura de tests unitarios.

---

## [0.0.2] — 2026-05-22

### Cambiado
- Repositorio separado en dos: `geaiq_metadata` (datos YAML) y `geaiq_mdp` (código Python/tooling).
- Comando CLI renombrado de `gemd` a `giqmd`.
- Módulo de entrada renombrado de `gemd.py` a `giqmd.py`.

---

## [0.0.1] — En desarrollo

### Agregado

**Pipeline principal**
- CLI `giqmd` con comandos `init`, `check`, `deploy`, `reset`, `import`, `menu`, `tags`.
- Contextos de ejecución: `none`, `file`, `all`, `stdin`, `commit`, `docker`.
- Soporte de entornos: `dev`, `prod`, `test`, `local`.
- Reporte de ejecución en formatos `plain`, `markdown`, `html`, `json`.
- Publicación automática de reportes en GCS con URL pública.
- Notificación de inicio y fin de tarea vía Google Chat webhook.

**Validación (`check`)**
- `BigQuerySourceProcessor`: dry-run de queries SQL, validación de schema, estimación de costos.
- `ShapeProcessor`: descarga y validación de shapefiles desde Google Drive (soporta ZIP).
- Validación del campo `gid` (shape ID) en el resultado del query.
- Flag `--only-new` para ignorar fuentes ya existentes en la API.
- Detección de nombres de columna duplicados.

**Despliegue (`deploy`)**
- Creación de observables, fuentes, períodos, columnas y dimensiones en la API.
- Carga de geometrías de shapefiles.
- Flag `--only-new` para saltear fuentes ya desplegadas.

**Parseo YAML**
- `PersistentAnchorYAML`: anclas YAML persistentes entre múltiples archivos.
- Soporte para `!ColumnRef` para referencias dinámicas a columnas.
- Tags custom: `!ObservableScale`, `!Period`, `!ObservableGroup`, `!Class_`, `!Indicator`.
- Datos de referencia en `data/` (scales, periods, attributes, obs_classes, indicators).

**Modelos de datos**
- `Source` con campos: `slug`, `status`, `description`, `ref`, `methodological_notes`, `source_type`, `source`, `shape`, `columns`, `select`, `transform`.
- `Column` con `name`, `unit`, `period`, `reliability`, `default_value`, `dimensions`.
- `Dimension` con `name`, `group`, `dependant`.
- `ObservableScale`, `ObservableGroup`, `Period`, `Class_`.
- Enums: `SourceStatus`, `SourceType`, `MeasurementUnit`, `ReliabilityType`, `ObservableScaleEnum`.
- Máquina de estados: `draft → ready → valid → deployed/done`.

**Caché**
- Caché pickle local en `~/.geoecon-cache/`.
- Invalidación con `--invalid-cache` y `--clean-full-cache`.
- Comando `giqmd reset` para limpiar caché, logs y shapefiles por fuente.

**Infraestructura**
- `Dockerfile` para Cloud Run Jobs (Python 3.11 slim).
- `cloudbuild.yaml`: build → push a Artifact Registry → deploy Cloud Run Job.
- `Makefile` con targets `sync`, `check-metadata`, `deploy-metadata`, `reset-metadata`.
- `giqmd import` para ingestión desde Google Sheets.
- `giqmd menu check` / `giqmd tags upload` para gestión de menús y tags.

**Cobertura de países** (archivos de metadatos presentes)
- Argentina, Brasil, Colombia, Chile, Perú, México, Bolivia, Paraguay, Uruguay, Ecuador, Venezuela, Guatemala, Honduras, El Salvador, Nicaragua, Costa Rica, Panamá, Cuba, República Dominicana, Haití, Belice, Jamaica, Puerto Rico.

### Cambiado
- Transición de PyYAML a `ruamel.yaml` para soporte de YAML 1.2 y anclas avanzadas.
- Migración de Pydantic v1 a Pydantic v2 (validadores `@field_validator`, `@model_validator`).
- Reporte de estado del source en el campo `reports:` del YAML (URLs de check/deploy/menu).

### Corregido
- Query para Argentina 2023 préstamos (`arg2023-prestamos-adm01`): corrección de `gid` para departamentos de La Rioja.
- `transform.on.observable_without_observation`: normalización del valor por defecto a `0.0`.
- Nombre de columnas en múltiples fuentes de Argentina (CFU, PBG, PBI, NASA, IGN).
- Manejo de encoding en la carga de shapefiles (detección automática con `chardet`).

---

### Notas de migración

Al actualizar modelos Pydantic, el caché pickle existente puede quedar inválido. Ejecutar:

```bash
giqmd --clean-full-cache check ...
# o manualmente:
rm -rf ~/.geoecon-cache/
```
