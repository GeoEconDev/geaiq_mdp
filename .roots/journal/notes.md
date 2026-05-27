# geaiq_mdp – Notes

> Ideas pendientes, observaciones técnicas, gotchas. Lo que un agente/dev debe saber antes de tocar.

---

## Gotchas críticos (releer antes de tocar el pipeline)

- **`load_data()` ANTES de `parse_metadata()`** con el MISMO reader/`PersistentAnchorYAML`. Sino las anclas `*ScaleX`/`*PerYYYY`/`*GroupX` no resuelven → ParseError. (Invariante #1 del DESIGN.)
- **Cache pickle sin versión** (`~/.geoecon-cache/`): tras cambiar un modelo Pydantic, corré `giqmd --clean-full-cache` o vas a ver `AttributeError` crípticos que NO parecen del cache. (TECH-01)
- **`typo` = "tipo"** (no error de tipeo) en `ObservableScale`/`Class_`/`ObservableGroup`. Valores: abstract/UTA/UTS/location.
- **`!ColumnRef <col>`** referencia una columna del resultado del query; si la columna no existe, falla recién en runtime del `processor.py` (sin validación temprana).
- **`status: deployed` vs `done`**: semántica ambigua, no filtrar a ciegas. (TECH-02)
- **El stack de anclas** (`push/pop_anchors` en `io_sources.py`) puede quedar inconsistente si el loop de `iter_sources` se interrumpe entre archivos.

## Observaciones de arquitectura

- El destino del deploy es configurable por `source.platform` (bigquery hoy operativo; **postgresql es placeholder**). Implementar el PostgreSQLSourceProcessor desbloquea persistir en postgres (pedido del ecosistema GeoEcon).
- `MeasurementUnit` (enum, 24 unidades) es la **fuente canónica de la unidad** de un indicador. El repo padre tiene una tarea de "unit del modelo, no heurística" que se resuelve leyendo de acá (vía la API). Falta extender el enum (CO2eq, Kelvin, µg/m³).
- `ObservableScaleType` (abstract/UTA/location/point) = la dimensión geográfica reusable que el repo padre identificó como `geoecon.scale`.
- `Period` ya tiene `start_date`/`end_date` acá (a diferencia del `geoecon.period` minimal de Odoo) → al sincronizar dimensiones, esta es la fuente con estructura temporal.

## Ideas / pendientes

- Mocks de BigQuery/API para que los tests de integración no necesiten credenciales.
- Unificar idioma de logs (es/en) para grep en prod (TECH-07).
- Limpiar campos muertos de los YAML (`state`, `old_source`) — inflan archivos y `old_source` es peligroso (queries obsoletas).

## Relación con el ecosistema

Este repo es el **"data plane"** del marco de abstracción de datos del repo padre `geoecon_map` (ver su `.roots/docs/design-data-abstraction.md` + ADR-041/042/043). El flujo Analista→YAML→giqmd→warehouse es la vía canónica definición→persistencia. Los indicadores "vivos" (APIs externas) se modelarían extendiendo `Source` (`retrieve_method: api` + contrato de latencia) dentro de este pipeline.
