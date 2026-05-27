# geaiq_mdp – Architecture Decisions

> ADRs portados del `DESIGN.md` del repo (27 May 2026) + decisiones nuevas. Primera persona plural.

---

## ADR-001 – YAML como lenguaje de datos (no JSON, no Python)

**Decisión:** todos los metadatos en YAML. **Motivación:** los analistas no son programadores; YAML es legible/editable sin IDE, soporta multilínea (`|`) para notas metodológicas, y el sistema de anclas (`&`/`*`) evita duplicar scales/periods/groups. Git history auditable. **Trade-off:** requiere un parser custom con anclas persistentes entre archivos (`PersistentAnchorYAML` sobre ruamel.yaml).

## ADR-002 – Anclas YAML persistentes entre archivos (`PersistentAnchorYAML`)

**Decisión:** las anclas de `data/` están disponibles en todos los archivos de `metadata/`. **Motivación:** sin esto, cada archivo redefiniría `ScaleNivelAdministrativo1`, `Per2023`, etc. → drift. **Implementación:** stack de anclas; `push_anchors()` snapshotea tras cargar `data/`, se restaura antes de cada archivo. **Invariante:** `load_data()` antes de cualquier `parse_metadata()` con el mismo reader.

## ADR-003 – Pydantic v2 para validación

**Decisión:** modelos en Pydantic v2 + `TypeAdapter` para listas. **Consecuencia:** validación declarativa, pero los cambios de esquema invalidan el cache pickle (TECH-01) — falla críptica si no se limpia el cache.

## ADR-004 – Máquinas de estado granulares (Source + Column)

**Decisión:** `SourceStatus` y `ColumnStatus` (draft→ready→valid→deployed/done, +error/failed) controlan qué operaciones corren. La columna tiene estado independiente → **deploy incremental**. Solo el analista avanza el estado; el tooling solo retrocede a error/failed.

## ADR-005 – Dos tipos de fuente (SQL + Shape), procesadores swap-ables

**Decisión:** `source.type` ∈ {sql, shape}; `source.platform` ∈ {bigquery, postgresql, googledrive}. Factory `get_processor((type, platform))`. SQL = tabular (BigQuery/Postgres), Shape = vectorial (Drive). Mismo pipeline, procesador distinto. **Estado:** `PostgreSQLSourceProcessor` es placeholder (NotImplementedError) — su implementación es la persistencia-a-postgres pendiente.

## ADR-006 – Caché pickle local

**Decisión:** `~/.geoecon-cache/` con decorator `@cache()` para no re-querear BigQuery (costo+latencia). **Trade-off:** no distribuido, sin TTL, **sin versionado de schema** (TECH-01), no thread-safe. El usuario invalida con `--clean-full-cache`.

## ADR-007 – Contextos de ejecución (`--context`)

**Decisión:** el mismo comando sirve local (`none`/`file`/`all`) y en CI/CD (`commit`/`docker`). `docker` baja el tarball del commit desde la GitHub API. Desacopla la selección de archivos del comando.

## ADR-008 – Reportes como artefactos públicos (GCS) + Google Chat

**Decisión:** Cloud Run Job no tiene terminal interactivo → el reporte HTML se sube a GCS (URL pública) y se notifica por Google Chat. El analista ve resultados sin SSH.

## ADR-009 – Slug canónico `{iso3}{año}-{concepto}-{escala}`

**Decisión:** identificador único, legible, que codifica jurisdicción/año/granularidad (ej. `arg2023-prestamos-adm01`).

## ADR-010 – Branches por colaborador + `make sync`

**Decisión:** `develop` + una rama por analista (`cr`/`jp`/`jm`/`vs`/`na`/`fc`), merge sin PR automatizado con `make sync`. **Motivación:** evita conflictos YAML cuando varios analistas tocan distintos países.

## ADR-011 – DSL de menú separado del ciclo de vida de fuentes

**Decisión:** el menú (`menu/`) es independiente; permite reorganizar la navegación sin re-desplegar datos. `giqmd menu check` + `tags upload`.

---

## ADR-012 – Bootstrap del sistema `.roots/` en el repo (27 May 2026)

**Decisión:** dar de alta `.roots/` (modo `source`, seed v1.5) como memoria persistente del repo, releyendo README/DESIGN/AGENTS/BACKLOG/CHANGELOG + código. **Motivación:** documentación técnica navegable + memoria para agentes/devs, alineada con el ecosistema GeoEcon (repo padre `geoecon_map`). Deuda técnica del `BACKLOG.md` portada a `tasks/todo.md`.
