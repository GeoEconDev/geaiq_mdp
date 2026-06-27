# CHANGELOG

Historial de cambios del proyecto geaiq_mdp.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## 2026-06-27 — v0.1.0a28: check_observables falla claro cuando ningún group_id matchea geometrías

**Resumen:** `check_observables` hacía un `merge` outer entre la data y las geometrías y, cuando los `group_id` (shape.id) **no matcheaban ninguna** geometría, caía silenciosamente al path de autoagregación ("More observables than data") → el **check pasaba "Ok" con 0 datos cargables** y recién el `deploy` fallaba. Caso real: `arg-2022-categoria-ocupacional` con `to_char(id_mod, '00000')` produciendo `' 06413'` (6 chars con espacio inicial) en vez de `'06413'` → 0/513 matches. Ahora, si **ningún** `group_id` de la data matchea una geometría del grupo, el check emite un **error** explícito (con muestra de data vs geometrías y, si detecta espacios, pista de usar `FM00000`). Mini-prueba defensiva: garantiza que el shape.id realmente referencia geometrías existentes antes de habilitar el deploy.

### Cambios

- **`src/geaiq_mdp/processor.py`**: `check_observables()` agrega un guard de cobertura — si `data_ids & obs_ids` es vacío, `self.error(...)` + `return False` (antes pasaba a autoagregación silenciosa).

## 2026-06-27 — v0.1.0a27: fix KeyError 'group_id' en do_source_selection con shape.id ref + ignore lista

**Resumen:** `do_source_selection()` filtraba con `df["group_id"]`, pero en `read_source()` el rename a `group_id` (`df.rename({shape.id.ref: "group_id"})` / `df.assign(group_id=...)`) ocurre en el paso **siguiente** del pipe. Cuando `shape.id` es un `!ColumnRef` (la columna todavía se llama como el ref, ej. `gid`) **y** `select.data.ignore` es una lista, el `df["group_id"]` lanzaba `KeyError: 'group_id'`. Se reproducía con `arg-2022-categoria-ocupacional` (`shape.id: !ColumnRef gid` + `ignore: [comunas/departamentos inválidos]`). Ahora se resuelve el nombre real de la columna (`shape.id.ref` cuando es ref, sino `"group_id"`). La rama `dict` del mismo método ya era correcta (usaba `column.ref`).

### Cambios

- **`src/geaiq_mdp/processor.py`**: `do_source_selection()` resuelve `group_col` desde `shape.id.ref` cuando `shape.id` es ref; el filtro de lista usa `df[group_col]` en vez de `df["group_id"]`.

## 2026-06-16 — v0.1.0a26: fix GeoEconAPIMultipleItems al resolver escalas abstractas por grupo

**Resumen:** `ObservableScale.set_group()` solo asignaba el grupo cuando la escala tenía `abstract_scale` (escala concreta). Para escalas abstractas como "Anexo" (sin padre), `if self.abstract_scale:` era `False` y `group_uuid` quedaba `None`. Al consultar la API con `name='Anexo', group_uuid=None`, devolvía múltiples resultados de distintos grupos (`arg_uni`, `arg_cue`), lanzando `GeoEconAPIMultipleItems`. Ahora `set_group()` siempre asigna el grupo. También se corrigió un bug de variable shadowing en `get_scale()` para el caso `str` donde la condición de filtro era siempre `False`.

### Cambios

- **`src/geaiq_mdp/models/wh.py`**: `set_group()` elimina la guarda `if self.abstract_scale:` — ahora siempre setea `self.group = group`.
- **`src/geaiq_mdp/processor.py`**: `get_scale()` caso `str` — renombra variable interna del generador para evitar shadowing con el `s` string externo; agrega `default=None` al `next()`.

---

## 2026-06-16 — v0.1.0a25: tipos de datos en campos + fix CRS naive geometry + fix finally bug

**Resumen:** Tres mejoras en una:
1. El reporte de "Query return fields" ahora muestra el tipo de dato de cada columna (`{campo: tipo}`) en lugar de solo los nombres.
2. `check_geometry()` setea EPSG:4326 como CRS cuando la geometría es "naive" (sin CRS), en lugar de fallar con "Cannot transform naive geometries". Aplica a fuentes con `latitude`/`longitude` explícitos (WGS84 implícito).
3. Bug fix: `finally: return True` en `check_geometry()` overrideaba el `return False` del except, haciendo que errores de geometría siempre retornaran `True`.

### Cambios

- **`src/geaiq_mdp/airflow_pg.py`**: `test_source()` consulta `pg_type` para obtener nombres de tipo PostgreSQL por OID y los retorna como `retrieved_column_types`.
- **`src/geaiq_mdp/bigquery.py`**: `test_source()` agrega `retrieved_column_types` desde `f.field_type` del schema de BigQuery.
- **`src/geaiq_mdp/processor.py`**: `check_query()` muestra `{nombre: tipo}` en "Query return fields" si hay tipos disponibles. `check_geometry()` llama `set_crs(epsg=4326)` con warning cuando CRS es None; elimina `finally: return True`.

---

## 2026-06-16 — v0.1.0a24: fix check_geometry falla cuando GeoDataFrame no tiene CRS

**Resumen:** `check_geometry()` llamaba `geodata.crs.to_string()` sin verificar que `crs` no sea `None`. Cuando la geometría construida no tiene CRS asignado, esto lanzaba `AttributeError: 'NoneType' object has no attribute 'to_string'`.

### Cambios

- **`src/geaiq_mdp/processor.py`**: `check_geometry()` verifica `geodata.crs is not None` antes de llamar `.to_string()`; si es `None` reporta `"No CRS defined"`. También se corrigió el doble paréntesis en el nombre del mensaje `((CRS))`.

---

## 2026-06-16 — v0.1.0a23: fix run_query usa get_conn() directo en lugar de get_pandas_df()

**Resumen:** `run_query()` usaba `hook.get_pandas_df()` que en versiones recientes de `apache-airflow-providers-postgres` delega en SQLAlchemy 2.x, cuyo objeto `Connection` no tiene `.cursor()`. Esto causaba `AttributeError: 'Connection' object has no attribute 'cursor'` al ejecutar la query real. La fix reemplaza `get_pandas_df()` por `hook.get_conn()` + `pd.read_sql()` directamente, igual que ya hace `test_source()`.

### Cambios

- **`src/geaiq_mdp/airflow_pg.py`**: `run_query()` usa `hook.get_conn()` + `pd.read_sql(query, conn)` en lugar de `hook.get_pandas_df()`.

---

## 2026-06-16 — v0.1.0a22: fix PostgreSQL column detection + mejora reporte con conteo de registros

**Resumen:** `AirflowPostgreSQLProcessor.test_source()` siempre devolvía `retrieved_column_names: []` porque `EXPLAIN` no retorna el esquema de columnas. Esto hacía que `check_query` reportara "Query does not solve all columns" para **todos** los campos declarados en fuentes PostgreSQL, aunque el query los incluyera. Además, el reporte no dejaba claro si la query se ejecutó ni cuántos registros devolvió.

### Cambios

- **`src/geaiq_mdp/airflow_pg.py`**: `test_source()` ahora ejecuta `SELECT * FROM (...) LIMIT 0` para obtener los nombres reales de columnas del query vía `cursor.description`, eliminando el falso positivo de "Query does not solve all columns".
- **`src/geaiq_mdp/processor.py`**: `check_stats()` emite `[INFO] Query returned N records` como mensaje dedicado antes del bloque Stats detallado.
- **`src/geaiq_mdp/processor.py`**: `check_query()` emite `[INFO] Query structure OK` con conteo de columnas validadas al finalizar sin errores.

---

## 2026-06-16 — v0.1.0a21: fix report_url usa URL interna Docker en vez de URL pública

**Resumen:** `GeoEconAPIDev` y `GeoEconAPIProd` usaban `GEAIQ_API_URL` (apunta a `http://geaiq_api:8000`, la URL interna del contenedor) para construir `static_uri`, que es la base de la `report_url` devuelta por `upload_report()`. El browser no puede acceder a esa URL. Ahora se usa `GEAIQ_API_PUBLIC_URL` (con fallback a `GEAIQ_API_URL`) para `static_uri`, mientras `api_uri` sigue usando `GEAIQ_API_URL` para las llamadas internas.

### Cambios

- **`src/geaiq_mdp/geoecon_api.py`**: `static_uri` usa `GEAIQ_API_PUBLIC_URL` si está definida; `api_uri` sigue usando `GEAIQ_API_URL` para acceso interno.

---

## 2026-06-16 — v0.1.0a20: fix QueryNotSolveAllColumns — AttributeError al reportar columnas faltantes

**Resumen:** `check_query` construía `column_not_found` como un `set` de strings (nombres de columna), pero luego iteraba `[c.name for c in column_not_found]` tratando cada string como un objeto con atributo `.name`. Esto causaba `AttributeError: 'str' object has no attribute 'name'` en cualquier fuente con columnas sin resolver en la query.

### Cambios

- **`src/geaiq_mdp/processor.py`**: `raise QueryNotSolveAllColumns(list(column_not_found))` en lugar de `[c.name for c in column_not_found]`.

---

## 2026-06-16 — v0.1.0a19: fix conn_id por defecto en AirflowPostgreSQLProcessor

**Resumen:** El default `postgres_conn_id="postgres_default"` causaba `The conn_id postgres_default isn't defined` porque esa conexión no existe en Airflow. Se cambia el default a `postgres_staging`, que sí está definida. Para fuentes que requieran otra conexión se puede crear `mdp.{slug}` en Airflow y `resolve_conn_id` la usará automáticamente.

### Cambios

- **`src/geaiq_mdp/airflow_pg.py`**: `postgres_conn_id` default cambiado de `"postgres_default"` a `"postgres_staging"`.

---

## 2026-06-16 — v0.1.0a17: fix AttributeError en checker y deployer al llamar get_source

**Resumen:** `checker()` y `deployer()` llamaban `target.get_source(src)` sobre el parámetro `target`, que es un enum `Environments` (string enum sin ese método). `get_source` es un método de `GeoEconAPI`. El error causaba que cualquier ejecución del DAG `metadata_processor` fallara con `AttributeError: 'Environments' object has no attribute 'get_source'`.

### Cambios

- **`src/geaiq_mdp/checker.py`**: importa `GEOECON_API_MAP`; instancia `geoecon_api = GEOECON_API_MAP[target]()` una sola vez antes del loop (solo cuando `only_new=True`); reemplaza `target.get_source(src)` por `geoecon_api.get_source(src)`.
- **`src/geaiq_mdp/deployer.py`**: ídem.

---

## 2026-06-05 — v0.1.0a16: fix versión del CLI siempre mostraba 0.1.0a10

**Resumen:** `version.py` tenía la versión hardcodeada en un diccionario que nunca se actualizaba al subir la versión del paquete. `get_version_string()` siempre retornaba `0.1.0a10` independientemente de la versión instalada. Se reemplazó por `importlib.metadata.version()` que lee la versión real del paquete instalado.

### Cambios

- **`src/geaiq_mdp/version.py`**: reemplaza el dict `VERSION` hardcodeado por `importlib.metadata.version("geaiq_mdp")`.

---

## 2026-06-05 — v0.1.0a15: Migración de tests a pytest

**Resumen:** Los tests del proyecto fueron migrados a pytest. Se agregó configuración de pytest en `pyproject.toml` y en `.vscode/settings.json` para que VS Code los descubra automáticamente.

### Cambios

- **`pyproject.toml`**: agrega dependencia opcional `test = ["pytest", "pandas"]`; agrega sección `[tool.pytest.ini_options]` con `testpaths = ["src/tests"]` y `pythonpath = ["src"]`.
- **`.vscode/settings.json`** (nuevo): habilita pytest en VS Code apuntando a `src/tests`.
- **`test_query.py`**: agrega `pytest.mark.skip` (requiere credenciales BigQuery).
- **`test_report.py`**: elimina `if __name__ == "__main__"` e import comentado.
- **`test_yml_anchor.py`**: reemplaza la clase duplicada `PersistentAnchorComposer` por import desde el módulo; convierte el script en dos tests con assertions y `pytest.raises`.
- **`test_yml_data.py`**: corrige bug (reader pasado como root); convierte a tests con fixture `tmp_path`.
- **`test_yml_parsing.py`**: convierte el script con prints en tests con assertions sobre tipos y valores.

---

## 2026-06-05 — v0.1.0a14: ExitCode enum; EXIT_MAP eliminado de giqmd

**Resumen:** `EXIT_MAP` reemplazado por el enum `ExitCode(int, Enum)` en `enums.py`. Esto permite que el DAG de Airflow importe `ExitCode` desde `geaiq_mdp.enums` (módulo liviano, sin dependencias pesadas) sin arrastrar el import de `gspread` que vivía en `giqmd.py`.

### Cambios

- **`enums.py`**: agrega `ExitCode(int, Enum)` con miembros `info=0`, `ok=0`, `warning=1`, `error=2`.
- **`giqmd.py`**: elimina definición local de `EXIT_MAP`; importa `ExitCode` desde `enums`; actualiza usos en `worst_report_type()` y `ctx.exit()`.

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
