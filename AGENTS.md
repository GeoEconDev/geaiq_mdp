# AGENTS.md — Guía para agentes de IA

Este archivo describe el proyecto para agentes de IA (Claude Code, Copilot, etc.) que necesiten trabajar en el repositorio.

## Qué hace este proyecto

GeaIQ Metadata es una herramienta CLI (`giqmd`) que:
1. Lee archivos YAML en `metadata/{país}/{fuente}.yml`
2. Los valida (dry-run en BigQuery o descarga de shapefiles)
3. Los despliega a la API REST de GeaIQ
4. Genera reportes HTML/Markdown que se publican en GCS

No es una aplicación web ni un servicio. Es un pipeline de procesamiento de datos geoeconómicos que corre localmente o como Cloud Run Job.

## Entry points

| Punto de entrada | Descripción |
|---|---|
| `src/geoecon_metadata/gemd.py` | CLI principal (Click). Toda funcionalidad pública parte de aquí. |
| `src/geoecon_metadata/checker.py` | `checker()` — valida fuentes READY |
| `src/geoecon_metadata/deployer.py` | `deployer()` — despliega fuentes VALID |
| `src/geoecon_metadata/data.py` | `load_data()` — **debe llamarse primero** para cargar anclas YAML globales |

## Flujo de datos (simplificado)

```
load_data(root, reader)          # carga data/ en el PersistentAnchorYAML
  └─ iter_sources(files, reader) # parsea metadata/*.yml usando las anclas
       └─ source_type_processors[src.source_type]().check(src, target)
            ├─ BigQuerySourceProcessor → dry_run en BQ
            └─ ShapeProcessor         → descarga shapefile de Drive
```

**Invariante crítica**: `load_data()` y `parse_metadata()` deben compartir el mismo objeto `PersistentAnchorYAML`. Si se crea un reader nuevo antes de parsear metadatos, las anclas YAML (`*ScaleX`, `*PerYYYY`, etc.) no estarán disponibles y el parse fallará.

## Modelos de datos

Los modelos Pydantic están en `src/geoecon_metadata/models/`:

- `Source` (`models/source.py`) — modelo central. Representa un dataset completo.
- `Column` — columna de datos con dimensiones, período y unidad.
- `Dimension` — eje de clasificación de una columna (ej. "moneda", "sector").
- `ObservableScale` (`models/dimension.py`) — escala geográfica (país, provincia, municipio).
- `Period` — período temporal con fechas de inicio y fin.
- `GeoEconAPIModel` (`models/geoecon_api.py`) — clase base con métodos `create()`, `update()`, `subitems()`.

Los modelos usan Pydantic v2. Los validadores de campos usan `@field_validator`, los cruzados usan `@model_validator`.

## Enums relevantes

En `src/geoecon_metadata/enums.py`:

- `SourceStatus` — `draft | ready | valid | deployed | done | error | failed`
- `SourceType` — `query | shape | TODO`
- `MeasurementUnit` — 24 unidades (hogares, personas, moneda, área, porcentaje, ...)
- `ReliabilityType` — `trust | raw | computed | verified | estimated | aggregated | imputed | simulated | untrust`

## Archivos YAML: convenciones

### `data/` (datos de referencia)
- Cargados en orden alfabético al inicio de cada ejecución.
- Definen anclas globales (`&ScaleX`, `&PerYYYY`, `&GroupX`).
- Tipos registrados: `!ObservableScale`, `!Period`, `!ObservableGroup`, `!Class_`, `!Indicator`.
- **No modificar sin entender el impacto en todos los archivos de `metadata/`**.

### `metadata/{país}/{slug}.yml`
- Lista de objetos `Source`.
- El `slug` sigue el patrón `{iso3}{año}-{concepto}-{escala}` (ej. `arg2023-prestamos-adm01`).
- Solo se procesan fuentes con `status: ready` (check) o `status: valid` (deploy).
- Pueden referenciar anclas de `data/` con `*NombreAncla`.
- Campos con `!ColumnRef nombre` referencian dinámicamente el nombre de otra columna del resultado del query.

## Caché

- Ubicación: `~/.geoecon-cache/`
- Formato: pickle
- Clave: slug de la fuente
- Se invalida con `giqmd --invalid-cache` o `giqmd --clean-full-cache`
- **El caché puede quedar desincronizado si cambia la estructura de modelos Pydantic.** En ese caso borrar manualmente o usar `--clean-full-cache`.

## Tests

En `src/tests/`:

```bash
pytest src/tests/
```

Los tests son principalmente de integración y requieren credenciales GCP activas. No hay mocks de la API ni de BigQuery. Si los tests fallan sin conexión, es esperado.

## Cómo agregar una nueva fuente de datos

1. Crear `metadata/{país}/{slug}.yml` con `status: draft`.
2. Completar `description`, `ref`, `source_type`, `source`, `columns`.
3. Cambiar a `status: ready`.
4. Ejecutar `giqmd check metadata/{país}/{slug}.yml`.
5. Si pasa, cambiar a `status: valid`.
6. Ejecutar `giqmd --target dev deploy metadata/{país}/{slug}.yml`.
7. Verificar en el entorno dev; si todo está bien, `--target prod`.

## Cómo agregar un nuevo país

1. Crear carpeta `metadata/{país}/`.
2. Agregar el grupo geográfico del país en `data/` (ej. `data/10_{iso3}.yaml`) con su ancla `&Group{iso3}`.
3. Agregar las escalas concretas del país (municipios, provincias) si no existen.
4. Crear los primeros archivos de fuentes.

## Qué NO tocar sin coordinación del equipo

- `data/00_scales.yaml` — cambiar o renombrar anclas rompe todos los archivos de metadatos que las referencien.
- `src/geoecon_metadata/models/source.py` — cambios en campos de `Source` o `Column` invalidan el caché pickle existente.
- `src/geoecon_metadata/persistent_anchor_yaml.py` — el parser de YAML personalizado es frágil; cualquier cambio debe ir acompañado de tests.
- `src/geoecon_metadata/geoecon_api.py` — contratos con la API externa.

## Patrones comunes que confunden

**`typo` no es un error tipográfico**: es el nombre de campo usado para "type" en algunos modelos (convención interna heredada). `typo: abstract` significa que la escala es abstracta.

**`reader` debe pasarse explícitamente**: Si ves una función que acepta `reader=None` y crea uno internamente, eso es para uso standalone. En el pipeline normal, siempre se pasa el reader compartido desde `checker.py` o `deployer.py`.

**Los `!Tag` en YAML**: `!ObservableScale`, `!Period`, etc. son constructores YAML custom registrados en `readers.py::register()`. Sin llamar a `register(reader)` antes de cargar, el parser falla.
