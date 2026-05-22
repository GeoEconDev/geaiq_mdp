# CHANGELOG

Historial de cambios del proyecto GeaIQ Metadata.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

---

## [Unreleased]

### Por hacer
- Resolver bug en `parsers.py::dump_metadata` (variables `reader` y `filename` no definidas en scope).
- Agregar `.env.example` con todas las variables de entorno requeridas.
- Completar implementación de `update_period` en el cliente API.
- Aumentar cobertura de tests unitarios.

---

## [0.0.1] — En desarrollo

### Agregado

**Pipeline principal**
- CLI `gemd` con comandos `init`, `check`, `deploy`, `reset`, `import`, `menu`, `tags`.
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
- Comando `gemd reset` para limpiar caché, logs y shapefiles por fuente.

**Infraestructura**
- `Dockerfile` para Cloud Run Jobs (Python 3.11 slim).
- `cloudbuild.yaml`: build → push a Artifact Registry → deploy Cloud Run Job.
- `Makefile` con targets `sync`, `check-metadata`, `deploy-metadata`, `reset-metadata`.
- `gemd import` para ingestión desde Google Sheets.
- `gemd menu check` / `gemd tags upload` para gestión de menús y tags.

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
gemd --clean-full-cache check ...
# o manualmente:
rm -rf ~/.geoecon-cache/
```
