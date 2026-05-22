# GeaIQ Metadata

Plataforma CLI para validar y desplegar metadatos geoeconómicos en la API de GeaIQ. Los datos se describen en archivos YAML que el tooling procesa para validarlos contra BigQuery y cargarlos en los entornos de la API.

## Índice

- [Arquitectura en una línea](#arquitectura-en-una-línea)
- [Instalación](#instalación)
- [Configuración GCP](#configuración-gcp)
- [Flujo de trabajo](#flujo-de-trabajo)
- [Referencia CLI](#referencia-cli)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Formato de los archivos YAML de metadatos](#formato-de-los-archivos-yaml-de-metadatos)
- [Gestión de branches](#gestión-de-branches)
- [Makefile](#makefile)

---

## Arquitectura en una línea

```
metadata/*.yml  →  parse (PersistentAnchorYAML + Pydantic)
               →  check (BigQuery dry-run / shapefile download)
               →  deploy (GeaIQ API + BigQuery tables)
               →  report (HTML/Markdown → GCS public URL)
```

---

## Instalación

```bash
pip install -e .
# o bien, solo dependencias de desarrollo:
pip install -r requirements.txt
```

Requiere Python ≥ 3.11.

---

## Configuración GCP

```bash
# Seleccionar proyecto
gcloud config set project geoecon-dev

# Habilitar APIs necesarias
gcloud services enable sheets.googleapis.com drive.googleapis.com bigquery.googleapis.com

# Autenticación con los scopes requeridos
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/cloud-platform,\
https://www.googleapis.com/auth/drive,\
https://www.googleapis.com/auth/spreadsheets,\
https://www.googleapis.com/auth/bigquery
```

Variables de entorno relevantes (ver también `src/geoecon_metadata/gcp.py`):

| Variable | Descripción |
|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | Ruta al JSON de credenciales de servicio (alternativa a ADC) |
| `CHAT_WEBHOOK` | URL del webhook de Google Chat para notificaciones |
| `GIT_TOKEN` | Token de GitHub para contexto `docker` |
| `METADATA_GIT_REPO` | URL de la GitHub API del repositorio |
| `METADATA_DIR` | Directorio raíz de trabajo (por defecto `.`) |

---

## Flujo de trabajo

El ciclo de vida de un fuente de datos sigue esta máquina de estados:

```
draft → ready → (check) → valid → (deploy) → deployed/done
                                             ↘ error / failed
```

1. **Crear** el archivo `metadata/{pais}/{slug}.yml` con `status: draft`.
2. Completar todos los campos requeridos y cambiar a `status: ready`.
3. **Validar** con `giqmd check`:
   ```bash
   giqmd check metadata/argentina/mi_fuente.yml
   ```
4. Si el check pasa sin errores, cambiar a `status: valid`.
5. **Desplegar** con `giqmd deploy`:
   ```bash
   giqmd --target dev deploy metadata/argentina/mi_fuente.yml
   ```
6. Una vez desplegado en dev, repetir con `--target prod`.

---

## Referencia CLI

```
giqmd [OPTIONS] COMMAND [ARGS]...

Opciones globales:
  --context [none|file|all|stdin|commit|docker]
                    Modo de selección de archivos (default: none)
  --root PATH       Directorio raíz del repositorio (default: .)
  --target [dev|prod|test|local]
                    Entorno de despliegue (default: dev)
  --commit TEXT     Hash o referencia git (usado con --context docker)
  --clean-full-cache  Borra todo el caché local (~/.geoecon-cache/)
  --invalid-cache     Invalida el caché sin borrar archivos
  --upload-output     Sube el reporte a Google Drive
  --debug             Activa logging DEBUG
  --chat-webhook URL  Webhook de Google Chat

Comandos:
  init      Inicializa datos base (scales, periods, attributes) en la API
  check     Valida archivos YAML de metadatos
  deploy    Despliega fuentes validadas a la API
  reset     Limpia caché, logs y shapefiles de las fuentes indicadas
  import    Importa metadatos desde Google Sheets
  menu check   Valida archivos de menú
  tags upload  Sube tags desde el menú a la API
```

### Ejemplos comunes

```bash
# Validar un archivo individual
giqmd check metadata/argentina/arg2023-prestamos-adm01.yml

# Validar todos los archivos en el contexto actual de git (archivos modificados)
giqmd --context commit check

# Desplegar en dev con reporte HTML
giqmd --target dev deploy --format html --output report.html metadata/argentina/mi_fuente.yml

# Desplegar en producción
giqmd --target prod deploy metadata/argentina/mi_fuente.yml

# Limpiar caché de una fuente
giqmd reset metadata/argentina/mi_fuente.yml

# Inicializar datos de referencia (solo una vez por entorno)
giqmd --target dev init
```

---

## Estructura del repositorio

```
geaiq_metadata/
├── src/
│   └── geoecon_metadata/      # Paquete principal
│       ├── giqmd.py            # Entry point CLI (click)
│       ├── checker.py         # Orquesta la validación de fuentes
│       ├── deployer.py        # Orquesta el despliegue a la API
│       ├── parsers.py         # Parse YAML → modelos Pydantic
│       ├── data.py            # Carga archivos de data/ (anclas globales)
│       ├── readers.py         # Lectura de YAML con registro de tipos
│       ├── persistent_anchor_yaml.py  # YAML con anclas persistentes entre archivos
│       ├── io_sources.py      # Iteración sobre fuentes YAML según contexto
│       ├── processors.py      # BigQuerySourceProcessor, ShapeProcessor
│       ├── bigquery.py        # Cliente BigQuery (dry-run, ejecución)
│       ├── shape.py           # Descarga y validación de shapefiles
│       ├── geoecon_api.py     # Cliente HTTP de la GeaIQ API
│       ├── gcp.py             # Setup de credenciales GCP
│       ├── cache.py           # Caché pickle local (~/.geoecon-cache/)
│       ├── report.py          # Formateo de reportes (plain/md/html/json)
│       ├── models/            # Modelos Pydantic
│       │   ├── source.py      # Source, Column, Dimension
│       │   ├── geoecon_api.py # GeoEconAPIModel (base)
│       │   ├── dimension.py   # ObservableScale, ObservableGroup, Period
│       │   ├── menu.py        # MenuOption, IncludeOptions
│       │   └── wh.py          # Indicadores y generadores
│       └── enums.py           # Enums: SourceStatus, SourceType, MeasurementUnit...
├── data/                      # Datos de referencia (scales, periods, attributes)
│   ├── 00_scales.yaml
│   ├── 01_periods.yaml
│   ├── 02_attributes.yaml
│   └── ...
├── metadata/                  # Fuentes de datos por país
│   ├── argentina/
│   ├── brasil/
│   ├── colombia/
│   └── ... (23 países)
├── menu/                      # Definición de menús de la UI
├── Makefile                   # Targets de CI y sincronización de branches
├── Dockerfile                 # Imagen para Cloud Run Jobs
├── cloudbuild.yaml            # Pipeline de CI/CD en Google Cloud Build
└── pyproject.toml
```

---

## Formato de los archivos YAML de metadatos

Cada archivo en `metadata/` es una lista YAML de objetos `Source`. Los campos disponibles:

```yaml
- slug: arg2023-prestamos-adm01       # Identificador único: {iso3}{año}-{concepto}-{escala}
  status: ready                        # draft | ready | valid | deployed | done | error | failed

  # Documentación (texto libre, soporta multiline con |)
  description: |
    Descripción del dataset.
  ref: |
    Fuente oficial y URL.
  methodological_notes: |
    Notas metodológicas detalladas.
  comment: Observaciones internas.
  retrieve_method: Descripción del método de obtención.

  # Tipo de fuente
  source_type: query                   # query | shape
  reliability: trust                   # trust | raw | computed | verified | estimated | ...

  # Para source_type: query — consulta SQL de BigQuery
  source: |
    SELECT gid, valor
    FROM `proyecto.dataset.tabla`

  # Para source_type: shape — IDs de archivos en Google Drive
  # source:
  #   - 1AbC...xYz

  # Geometría: vincula la columna ID del shape con escala y período
  shape:
    id: !ColumnRef gid                 # columna del query que contiene el GID
    group: *GroupArg                   # ancla YAML del grupo geográfico
    period: *Per2023                   # ancla YAML del período

  # Selección de escalas observables
  select:
    observables:
      shape_scale:
        - *ScaleNivelAdministrativo0
        - *ScaleNivelAdministrativo1

  # Transformaciones sobre las observaciones
  transform:
    data:                              # remapeo de valores (opcional)
    on:
      observable_without_observation: use_defaults  # o: null

  # Columnas de datos
  columns:
    - name: loc08                      # nombre de la columna en el resultado del query
      period: !ColumnRef locfec        # columna que contiene la fecha del período
      unit: moneda                     # hogares | personas | moneda | área | porcentaje | ...
      reliability: raw
      default_value: 0.0
      dimensions:
        - name: sector privado no financiero
          group: prestamos
        - name: pesos argentinos
          group: moneda
```

### Anclas YAML disponibles

Las anclas se definen en `data/` y deben cargarse antes que cualquier archivo de metadatos. Las más usadas:

| Ancla | Tipo | Descripción |
|---|---|---|
| `*ScaleNivelAdministrativo0` | ObservableScale | País completo |
| `*ScaleNivelAdministrativo1` | ObservableScale | Provincias/departamentos |
| `*ScaleNivelAdministrativo2` | ObservableScale | Municipios/comunas |
| `*PerYYYY` | Period | Período anual (ej. `*Per2023`) |
| `*GroupArg`, `*GroupBra`, ... | ObservableGroup | Grupo geográfico por país |

---

## Gestión de branches

El repositorio usa un branch por colaborador que se sincroniza con `develop`:

| Branch | Colaborador |
|---|---|
| `develop` | Integración principal |
| `cr` | Cristian Rocha |
| `jp`, `jm`, `vs`, `na`, `fc` | Otros colaboradores |

```bash
# Actualizar todos los branches desde develop
make sync-from-develop

# Actualizar develop desde todos los branches
make sync-develop

# Ciclo completo (desde develop → ramas → develop)
make sync
```

---

## Makefile

| Target | Descripción |
|---|---|
| `make sync` | Sincronización bidireccional completa |
| `make sync-from-develop` | Actualiza branches de colaboradores desde develop |
| `make sync-develop` | Integra todos los branches en develop |
| `make clean-cache` | Borra `~/.geoecon-cache/` |
| `make clean-reports` | Borra reportes locales `report.*` |
| `make clean-logs` | Borra `~/.geoecon-logs/` |
| `make show-status` | Lista el `status:` de todos los archivos de metadatos |
| `make check-metadata file=metadata/pais/fuente.yml` | Ejecuta `giqmd check` en Cloud Run |
| `make deploy-metadata file=metadata/pais/fuente.yml` | Ejecuta `giqmd deploy` en Cloud Run |
| `make reset-metadata file=metadata/pais/fuente.yml` | Ejecuta `giqmd reset` en Cloud Run |
