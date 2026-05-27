# Modelos Pydantic + esquema YAML de metadatos

> Modelos en `src/geoecon_metadata/models/` + `enums.py`. El YAML que consumen vive en `geaiq_metadata`.

## Modelos (`models/`, Pydantic v2)

| Modelo | Archivo | Campos clave |
|---|---|---|
| **Source** | `source.py` | `slug`, `status`, `description`, `ref`, `methodological_notes`, `source` (SourceDefinition), `shape`, `columns`, `select`, `transform`, `validation`, `processing`, `disabled` |
| **Column** | `source.py` | `name`, `period` (ref o Period), `unit` (MeasurementUnit), `reliability`, `default_value`, `dimensions`, `topic`, `disabled`, `status`, `eval` |
| **SourceDefinition** | `source.py` | `type` (sql/shape), `platform` (bigquery/postgresql/googledrive), `query` o `files` |
| **Shape** | `source.py` | `id` (`!ColumnRef` columna GID), `group`, `period` (+ opcional `scale`, `obs_class`) |
| **Selection** | `source.py` | `observables` (`shape_scale: [...]`), `data` (`unique: [...]`) — qué subset procesar |
| **Validation** / **Transform** / **Processing** | `source.py` | observables esperados / transforms + `on.observable_without_observation: use_defaults\|null` / reanudación (`continue_from`, `update_geometry`) |
| **Dimension** | `dimension.py` | `name` (ref o str), `group`, `dependant` |
| **ObservableScale** | `wh.py` | `uuid`, `name`, `description`, `administrative_level`, `typo` (=tipo: abstract/UTA/UTS/location) + geometría |
| **ObservableGroup** | `wh.py` | `uuid`, `name`, `description`, `parent_group_uuid`, `typo` |
| **Period** | `wh.py` | `uuid`, `name`, `description`, `start_date`, `end_date` |
| **Attribute / ObservableClass** | `wh.py` | dimensiones de observables / clases |
| **MenuOption** | `menu.py` | `name`, `slug`, `scope`, `description`, `select`, `options` (anidado, `!Include`) |
| **GeoEconAPIModel** | `models/geoecon_api.py` | base: `geoecon_api_key()` (búsqueda), `geoecon_api_data()` (body), `get/create/update` |

**Tags YAML custom:** `!Source`, `!Column`, `!Period`, `!ObservableScale`, `!ObservableGroup`, `!Class_`, `!Dimension`, `!MenuOption`, **`!ColumnRef <col>`** (referencia dinámica a una columna del resultado del query).

## Enums (`enums.py`)

| Enum | Valores |
|---|---|
| **Environments** | prod, dev, local, test |
| **SourceStatus / ColumnStatus** | draft, ready, error, valid, deployed, failed, done |
| **SourceType** | query, shape, TODO |
| **SourcePlatform** | **bigquery, postgresql, googledrive** |
| **ReliabilityType** | trust, raw, computed, synthetic, verified, estimated, aggregated, imputed, simulated, untrust, TODO |
| **MeasurementUnit** (24) | hogares, viviendas, personas, votos, establecimientos, sedes, moneda, área, volumen, distancia, identificación, **temperatura**, densidad, tasa, variación, tiempo, peso, energía, velocidad, presión, frecuencia, ángulo, **concentración**, índice, unidades económicas… |
| **ObservableScaleEnum** | país, departamento, partido, distrito, provincia, municipio, isla, cantón, area no municipalizada, **point**, corregimiento, unidad federativa |
| **ObservableScaleTypeEnum** | abstract, UTA, UTS, **location**, cluster, functional region |
| **ObservableClassEnum** | 14 clases (territoriales, económicas, educativas, …) |

> **Relevante para el ecosistema GeoEcon:** `MeasurementUnit` es la fuente canónica de la unidad de un indicador (resuelve la tarea "unit del modelo, no heurística" del repo padre). `SourcePlatform` (postgresql) es el destino de persistencia configurable. `ObservableScaleType` (admin/UTA/location/point) = la dimensión geográfica reusable.

## Formato YAML de una Source (en `geaiq_metadata/metadata/{país}/*.yml`)

```yaml
- slug: arg2023-prestamos-adm01          # {iso3}{año}-{concepto}-{escala}
  status: ready                          # draft|ready|valid|deployed|done|error|failed
  description: |
    Descripción del dataset.
  ref: |
    Fuente oficial + URL.
  methodological_notes: |
    Notas metodológicas.
  reliability: trust                     # trust|raw|computed|verified|estimated|...
  retrieve_method: manual

  source:                                # NUEVO formato anidado
    type: sql                            # sql | shape
    platform: bigquery                   # bigquery | postgresql | googledrive
    query: |
      SELECT gid, valor FROM `proyecto.dataset.tabla`
    # (shape: files: [<drive_id|url>, ...])

  shape:
    id: !ColumnRef gid                   # columna con el GID
    group: *GroupArg                     # ancla del grupo geográfico (data/10_arg.yaml)
    period: *Per2023                     # ancla de período (data/01_periods.yaml)

  select:
    observables:
      shape_scale:
        - *ScaleNivelAdministrativo0
        - *ScaleNivelAdministrativo1

  transform:
    on:
      observable_without_observation: use_defaults   # o null

  columns:
    - name: loc08                        # columna del resultado del query
      period: !ColumnRef locfec          # o *Per2023
      unit: moneda                       # MeasurementUnit
      reliability: raw
      default_value: 0.0
      dimensions:
        - name: sector privado no financiero
          group: prestamos
        - name: pesos argentinos
          group: moneda
```

> Nota: existe un formato VIEJO (`source_type:` + `source:` plano) con migración a este anidado (`_migrate_old_format` en `source.py`). Ver `data/` de `geaiq_metadata` para las anclas (`*ScaleX`, `*PerYYYY`, `*GroupX`).
