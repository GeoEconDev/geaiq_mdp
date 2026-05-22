# DESIGN.md — Decisiones de arquitectura

Documento vivo que registra las decisiones técnicas importantes del proyecto y el razonamiento detrás de ellas.

## Visión general

GeaIQ Metadata resuelve un problema específico: existe un equipo distribuido de analistas que produce descripciones de datasets geoeconómicos en archivos YAML, y esos datasets deben terminar en una API REST con sus observaciones cargadas en BigQuery. El tooling actúa como el puente entre ambos mundos.

```
Analista → YAML → gemd check → gemd deploy → GeaIQ API / BigQuery
```

## Decisiones arquitectónicas

### 1. YAML como lenguaje de datos (no JSON, no Python)

**Decisión**: Todos los metadatos se expresan en YAML.

**Motivación**:
- Los analistas no son necesariamente programadores. YAML es legible y editable sin IDE.
- Permite texto libre multilínea (`|`) para campos como `methodological_notes`.
- El sistema de anclas YAML (`&` / `*`) permite reutilizar definiciones (scales, periods, groups) sin duplicación.
- El historial de Git sobre archivos YAML es legible y auditable.

**Trade-off**: El parser YAML necesita manejar anclas persistentes entre archivos, lo cual requirió implementar `PersistentAnchorYAML` sobre `ruamel.yaml`.

---

### 2. Anclas YAML persistentes entre archivos (`PersistentAnchorYAML`)

**Decisión**: Las anclas definidas en `data/` están disponibles en todos los archivos de `metadata/`.

**Motivación**: Sin esto, cada archivo de metadatos tendría que redefinir `ScaleNivelAdministrativo1`, `Per2023`, etc. Eso introduciría drift y errores de consistencia.

**Implementación**: `PersistentAnchorYAML` extiende el loader de `ruamel.yaml` manteniendo un stack de anclas entre cargas. El método `push_anchors()` hace snapshot del estado después de cargar `data/`, y ese snapshot se restaura antes de cada archivo de metadatos.

**Invariante**: `load_data()` debe ejecutarse antes que cualquier `parse_metadata()` con el mismo reader.

---

### 3. Pydantic v2 para validación de modelos

**Decisión**: Todos los modelos de datos usan Pydantic v2.

**Motivación**:
- Validación declarativa con mensajes de error claros.
- Serialización/deserialización integrada.
- Type hints como documentación ejecutable.
- `TypeAdapter` permite validar tipos complejos (ej. `List[Source]`) sin modelo wrapper.

**Trade-off**: La versión `0.0.1` en `pyproject.toml` no coincide con el estado real del proyecto — el modelo de datos es sustancialmente más maduro.

---

### 4. Máquinas de estados: `SourceStatus` y `ColumnStatus`

**Decisión**: Tanto la fuente como cada una de sus columnas tienen un `status` independiente.

```
draft → ready → valid → deployed
                      ↘ done
                      ↘ error
                      ↘ failed
```

**`SourceStatus`** controla el dataset completo: qué operaciones puede ejecutar el tooling (`check` solo toma `ready`, `deploy` solo toma `valid`).

**`ColumnStatus`** controla cada columna individualmente. Esto permite desplegar parcialmente un dataset: una columna puede estar en `deployed` mientras otra sigue en `draft` o está deshabilitada (`disabled: true`). Es el mecanismo para subir un dataset de forma incremental sin esperar que todas las columnas estén listas.

**Motivación**: En un equipo distribuido, el estado del archivo YAML es la única fuente de verdad compartida. La granularidad por columna refleja la realidad operativa: los datos de distintas variables no siempre están disponibles al mismo tiempo.

**Regla de negocio**: El analista es responsable de avanzar el estado manualmente. El tooling nunca retrocede el estado (excepto `error`/`failed` automáticos).

---

### 5. Dos tipos de fuente: `sql` y `shape`

**Decisión**: El tipo de fuente se declara en el campo anidado `source`, con `type: sql` o `type: shape`, junto con la plataforma de origen.

```yaml
source:
  type: sql           # consulta a una base de datos
  platform: bigquery  # bigquery | postgresql
  query: |
    SELECT ...

# o bien:
source:
  type: shape         # geometrías vectoriales
  platform: googledrive
  files:
    - id: 1ABC...
```

**Plataformas soportadas**:
- `type: sql` + `platform: bigquery` — consulta BigQuery (caso predominante)
- `type: sql` + `platform: postgresql` — consulta PostgreSQL
- `type: shape` + `platform: googledrive` — shapefile descargado de Google Drive

**Motivación**: Los datasets geoeconómicos tienen dos naturalezas:
- Datos tabulares que ya están en BigQuery (o se cargan ahí).
- Geometrías vectoriales (límites administrativos) que vienen de archivos SHP/GeoJSON.

Ambos tipos pasan por el mismo pipeline de validación y despliegue, pero con procesadores distintos (`BigQuerySourceProcessor` vs `ShapeProcessor`).

**Nota**: El campo plano `source_type` ya no está soportado. Toda fuente nueva debe usar la estructura anidada `source.type` + `source.platform`.

---

### 6. Caché pickle local

**Decisión**: Los resultados de queries y descargas se cachean en `~/.geoecon-cache/` con pickle.

**Motivación**: Las queries a BigQuery y las descargas de Drive son lentas y tienen costo. Cachear evita re-procesar fuentes que no cambiaron.

**Limitaciones conocidas**:
- No es thread-safe (problema si se corre en paralelo).
- No es distribuido (cada desarrollador tiene su caché local).
- Puede quedar stale si cambia la estructura de modelos Pydantic (invalidar con `--clean-full-cache`).
- No tiene TTL — el usuario debe invalidar manualmente o con `--invalid-cache`.

---

### 7. Contextos de ejecución (`--context`)

**Decisión**: El CLI soporta múltiples modos de selección de archivos.

| Contexto | Comportamiento |
|---|---|
| `none` | Archivos explícitos como argumentos |
| `file` | Lee lista de archivos desde un archivo de texto |
| `all` | Todos los YAML del repositorio |
| `stdin` | Lee rutas desde stdin |
| `commit` | Archivos modificados en el último commit |
| `docker` | Archivos modificados en un commit específico (para Cloud Run) |

**Motivación**: El mismo comando funciona localmente (donde el analista sabe qué archivo tocó) y en CI/CD (donde el contexto se deriva del commit de Git).

---

### 8. Reportes como artefactos públicos

**Decisión**: Los reportes se suben a GCS con URL pública y se notifica por Google Chat.

**Motivación**: El pipeline corre en Cloud Run, sin terminal interactiva. El reporte HTML en GCS es la única forma de que el analista vea los resultados de un check/deploy remoto.

**URL pattern**: `{api_base}/reports/{command}/{status}/report.{slug}.{command}.{env}.html`

---

### 9. Slug como identificador único

**Decisión**: El slug es el identificador canónico de una fuente. Formato: `{iso3}{año}-{concepto}-{escala}`.

Ejemplos: `arg2023-prestamos-adm01`, `bra2022-pib-adm01`, `col2021-poblacion-adm02`.

**Motivación**:
- Es legible en los logs y reportes.
- Codifica la jurisdicción, el año y la granularidad sin necesidad de consultar el archivo.
- Permite operaciones por patrón (ej. `ls ~/.geoecon-cache/*arg2023*`).

---

### 10. Branches por colaborador

**Decisión**: Cada analista trabaja en su propio branch (`cr`, `jp`, `jm`, etc.) y se integra periódicamente a `develop`.

**Motivación**: Evita conflictos en archivos YAML cuando múltiples analistas trabajan en distintos países simultáneamente. Los archivos de metadatos raramente se solapan entre países.

**Operación**: `make sync` sincroniza en ambas direcciones. No se usa Pull Request para la integración diaria — el Makefile automatiza los merges.

---

### 11. Modelos de control de datos: Selection, Validation, Transform, Processing

**Contexto**: En un dataset geoeconómico, los *observables* son las filas (equivalentes a las geometrías de un shapefile, p. ej. departamentos o municipios) y las *columnas* son los atributos medidos sobre ellos. El problema central es que las muestras de datos rara vez cubren todos los observables: puede haber más geometrías que datos, o más datos que geometrías, o fuentes oficiales que solo reportan un subconjunto del universo. El tooling no puede fallar silenciosamente ante estas situaciones — debe ponerlas sobre la mesa de forma explícita.

Los cuatro modelos a continuación son el mecanismo para declarar ese conocimiento en el YAML.

---

#### `Selection` — Selección del subconjunto a procesar

Agrupa la selección de observables y de datos. Permite delimitar qué parte del universo se va a procesar antes de validar o transformar.

```yaml
select:
  observables:
    shape_scale: adm01             # restringe la escala geométrica
    ignore:
      gid: ["0", "99"]             # excluye observables por valor de columna
    filtre:
      tipo: "urbano"               # filtra (solo incluye) por valor
  data:
    ignore:
      periodo: ["2020"]            # excluye filas del dataset por valor
```

**`ObservablesSelection`**: Opera sobre el lado de las geometrías/observables.
- `shape_scale`: escala de geometría a usar (cuando el shapefile tiene múltiples escalas).
- `ignore`: excluye observables específicos por valor (p. ej. filas de totales nacionales que no corresponden a una geometría real).
- `filtre`: filtra para incluir solo los observables que cumplan la condición.

**`DataSelection`**: Opera sobre el lado del dataset (filas de datos).
- `ignore`: excluye filas del dataset por valor (p. ej. códigos de "total" o "sin dato").

---

#### `Validation` — Validación de los observables seleccionados

Valida la cobertura entre observables y datos después de aplicar la selección.

```yaml
validation:
  observables:
    shape_scale: adm01
    ignore:
      gid: ["0"]
```

**`ObservablesValidation`**: Define qué observables deben estar presentes en los datos para que la validación sea exitosa. Tiene los mismos campos que `ObservablesSelection` (`shape_scale`, `ignore`), pero su semántica es declarativa: "estos son los observables que espero que existan; los que no están en los datos son un problema a reportar, no necesariamente un error fatal".

---

#### `Transform` — Transformaciones de datos y geometrías

Transforma los datos antes de cargarlos. Cubre dos necesidades: conversión de unidades/formato en los datos y simplificación de geometrías para reducir peso en base de datos.

```yaml
transform:
  shape:
    dissolve: true                 # disuelve geometrías agrupando por columna
  data:
    shape_scale: adm01
    clone:
      nueva_col: col_origen        # copia una columna bajo otro nombre
    update:
      col: "col * 1000"            # actualiza una columna con expresión
    substitute:
      codigo: {"01": "ARG01"}      # reemplaza valores específicos
    compute:
      col_nueva: "col_a + col_b"   # calcula columna nueva con expresión
  on:
    observable_without_observation: use_defaults   # qué hacer si no hay dato
```

**`ShapeTransform`**: Transforma geometrías. `dissolve` agrega polígonos para reducir resolución y peso.

**`DataTransform`**: Transforma el dataset tabular. Permite clonar, recalcular y sustituir valores.

**`OnTransform`**: Declara el comportamiento ante observables sin observación. `error` falla; `use_defaults` continúa con valores por defecto.

---

#### `Processing` — Procesamiento parcial con punto de continuación

Permite reanudar el procesamiento de un archivo desde un punto intermedio. Útil para datasets de gran volumen donde un error en medio del proceso no debería obligar a recomenzar desde cero.

```yaml
processing:
  continue_from: "ARG-1234"       # slug o id del observable desde donde continuar
  update_geometry: false          # si debe actualizar geometrías ya cargadas
```

---

### 12. DSL de Menú

**Decisión**: Los menús de la interfaz se describen en archivos YAML separados en `menu/`, con un DSL propio más sencillo que el de fuentes.

**Motivación**: El menú es independiente del ciclo de vida de las fuentes — puede actualizarse sin re-desplegar datos. Permite que el equipo de producto organice la navegación sin tocar los metadatos de análisis.

**Estructura**:

```yaml
# menu/aereo.yml
- name: Aeropuertos
  slug: aerop               # generado automáticamente de name si se omite
  description: |
    Un aeropuerto es una estación terrestre...
  select:
    dimensions:
      - name: Aeropuertos
        group: Instalaciones de transporte

- name: Helipuertos
  slug: helip
  description: |
    ...
  select:
    dimensions:
      - name: Helipuertos
        group: Instalaciones de transporte
```

**Campos de `MenuOption`**:
- `name` (requerido): Texto visible en el menú.
- `slug`: Identificador único. Si se omite, se genera con `slugify(name)`.
- `scope`: Alcance del tag en la UI (default: `"openning"`).
- `description`: Descripción visible al usuario.
- `select.dimensions`: Lista de dimensiones que este ítem de menú selecciona.
- `select.shape_groups`: Lista de grupos de geometrías asociados.
- `options`: Sub-items del menú (estructura recursiva).

**Punto de entrada**: `menu/menu.yml` con directiva `!Include` que agrega los archivos por temática:

```yaml
!Include menu/countries.yml menu/topics.yml
```

**Comandos**:
- `gemd menu check` — valida la estructura de los archivos `menu/`.
- `gemd tags upload` — sube los tags del menú a la API (`ui/tags`).

---

## Dependencias externas

| Servicio | Uso | Credenciales |
|---|---|---|
| Google BigQuery | Validación de queries (dry-run) y ejecución de datos | ADC / Service Account |
| Google Drive | Descarga de shapefiles | ADC con scope Drive |
| Google Sheets | Importación de metadatos vía `gemd import` | ADC con scope Sheets |
| Google Cloud Storage | Publicación de reportes HTML | ADC |
| Google Cloud Run | Ejecución remota del pipeline | `cloudbuild.yaml` |
| GitHub API | Contexto `docker` — lista de archivos por commit | `GIT_TOKEN` |
| GeaIQ API | Destino final de los metadatos | URL en `GEOECON_API_MAP` |

---

## Qué no hace este sistema

- No versiona los datos de observación (solo los metadatos).
- No detecta drift entre el YAML y lo que ya está en la API (fuera del flag `--only-new`).
- No tiene rollback automático de despliegues fallidos.
- No soporta despliegue incremental de columnas — si cambia una columna, hay que re-desplegar la fuente completa.
