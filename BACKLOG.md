# BACKLOG

Ítems derivados de la revisión de código (2026-05-19). Ordenados por prioridad dentro de cada categoría.

Criterio de priorización:
- **P0 — Bloqueante**: produce crashes o resultados incorrectos silenciosos.
- **P1 — Alta**: degrada confiabilidad o introduce riesgo de datos corruptos.
- **P2 — Media**: deuda técnica que frena la evolución del proyecto.
- **P3 — Baja**: mejora de calidad sin impacto operativo inmediato.

---

## P0 — Bloqueantes

### BUG-01 · `dump_metadata` está roto y nunca puede ejecutarse

**Archivo**: [src/geoecon_metadata/parsers.py](src/geoecon_metadata/parsers.py)

**Problema**: La función referencia `reader` y `filename` como si fueran parámetros, pero ninguno está en su firma. Es un copy-paste incompleto de `parse_menu`. Cualquier llamada lanzaría `NameError`.

**Acción**:
- Si la función no se usa: eliminarla.
- Si se necesita: definir la firma correcta `dump_metadata(src, filename, reader=None)` e implementar la lógica de serialización YAML.

**Esfuerzo**: XS (eliminar) / M (implementar correctamente)

---

### BUG-02 · `report[-1]` en `checker.py` asume estado previo implícito

**Archivo**: [src/geoecon_metadata/checker.py:24](src/geoecon_metadata/checker.py)

**Problema**: `report[-1]["sources"].append(...)` asume que `iter_sources` ya insertó un elemento en `report` antes de ejecutar el cuerpo del loop. Si `iter_sources` no produce ningún elemento pero agrega algo a `report` de forma tardía, o si la lógica cambia, esto produce `IndexError`. La invariante es invisible desde el código del checker.

**Acción**: Hacer explícita la relación entre `iter_sources` y `report`. Mínimo: agregar un `assert len(report) > 0` con mensaje descriptivo dentro del loop, o refactorizar para que el checker controle directamente la entrada en `report`.

**Esfuerzo**: S

---

### BUG-03 · `pip install` interno en `giqmd.py`

**Archivo**: [src/geoecon_metadata/giqmd.py:63-74](src/geoecon_metadata/giqmd.py)

**Problema**: El bloque `except ModuleNotFoundError` invoca los internals de pip para auto-instalarse. Esto es frágil (el API interno de pip no es estable), silencia el error real, y puede instalar versiones incorrectas en entornos controlados (virtualenv, Docker). En producción ya hay un `Dockerfile` que garantiza las dependencias — este código nunca debería ejecutarse en ese contexto.

**Acción**: Eliminar el bloque `try/except` completo. Reemplazar con un mensaje claro:
```
ModuleNotFoundError: instalar dependencias con 'pip install -e .' antes de usar giqmd.
```

**Esfuerzo**: XS

---

## P1 — Alta prioridad

### TECH-01 · Caché sin versionado: falla silenciosa tras cambios de modelo

**Archivo**: [src/geoecon_metadata/cache.py](src/geoecon_metadata/cache.py)

**Problema**: El caché usa pickle keyed por slug. Si cambia la estructura de un modelo Pydantic (`Source`, `Column`, etc.), el unpickle falla con un error críptico (`AttributeError` o `TypeError`) que el usuario no asocia con el caché. El `--clean-full-cache` existe pero requiere que el usuario sepa que debe usarlo.

**Acción**:
1. Incluir un hash de versión del schema en la clave del caché (puede ser el hash del módulo `models/source.py` o una constante `CACHE_VERSION` que se incrementa manualmente con cada cambio de modelo).
2. Al leer del caché, capturar `Exception` en el unpickle e invalidar automáticamente la entrada corrupta con un `logging.warning`.

**Esfuerzo**: S

---

### TECH-02 · Ambigüedad entre `status: deployed` y `status: done`

**Archivo**: [src/geoecon_metadata/enums.py](src/geoecon_metadata/enums.py), modelos y archivos `metadata/`

**Problema**: Ambos valores existen en `SourceStatus` pero no hay documentación ni validación que explique cuándo usar uno u otro. Los archivos de metadatos usan ambos de forma inconsistente. Esto puede afectar filtros en el pipeline si alguna condición solo chequea uno de los dos.

**Acción**:
- Definir claramente la diferencia (ej. `deployed` = en dev, `done` = en prod y verificado).
- Si son sinónimos: deprecar uno, migrar todos los archivos YAML al otro, eliminar el valor obsoleto.
- Documentar la decisión en [DESIGN.md](DESIGN.md).

**Esfuerzo**: S (decisión) + M (migración de archivos)

---

### TECH-03 · Variables de entorno sin `.env.example`

**Problema**: Las variables de entorno requeridas (`GIT_TOKEN`, `CHAT_WEBHOOK`, `METADATA_GIT_REPO`, etc.) están dispersas en el código. Un colaborador nuevo no sabe qué necesita configurar sin leer los fuentes.

**Acción**: Crear `.env.example` con todas las variables documentadas, sus valores de ejemplo y si son obligatorias u opcionales. Referenciar desde el README.

**Esfuerzo**: XS

---

### TECH-04 · `update_period` no implementado en el cliente API

**Archivo**: [src/geoecon_metadata/geoecon_api.py](src/geoecon_metadata/geoecon_api.py)

**Problema**: El método existe pero lanza `NotImplementedError` (o equivalente). Si `giqmd init --update` intenta actualizar períodos, falla en runtime sin que el usuario tenga forma de saberlo de antemano.

**Acción**: Implementar el método o, si la API no soporta el endpoint todavía, agregar un `logging.warning` explícito y omitir la operación sin abortar.

**Esfuerzo**: S (depende del contrato de la API)

---

## P2 — Deuda técnica media

### TECH-05 · Campo `typo` confunde a cualquier lector nuevo

**Archivos**: [src/geoecon_metadata/models/dimension.py](src/geoecon_metadata/models/dimension.py), archivos `data/*.yaml`

**Problema**: `typo: abstract` parece un error tipográfico de `type`. El nombre viene de una convención interna pero no está documentado en ningún lugar. Dificulta onboarding y confunde a agentes de IA y linters.

**Acción**: Renombrar el campo a `kind` en el modelo Pydantic usando `alias="typo"` para mantener compatibilidad con los archivos YAML existentes. Documentar la decisión. Migración progresiva de los YAML en una segunda fase.

**Esfuerzo**: M

---

### TECH-06 · Campos muertos en los archivos YAML (`state`, `source_message`, `old_source`)

**Archivos**: múltiples en `metadata/`

**Problema**: Campos con valores vacíos (`state:`, `source_message:`) y `old_source:` con queries obsoletas inflan los archivos sin aportar información. `old_source` en particular es especialmente peligroso: guarda SQL antiguo que puede confundir a quien edita el archivo.

**Acción**:
1. Si `state` y `source_message` son funcionales: documentar su propósito. Si no: eliminarlos del modelo y de todos los YAML.
2. Eliminar el campo `old_source` de todos los archivos YAML. El historial de Git cumple esa función.
3. Crear un script de limpieza (`make clean-dead-fields`) que detecte estos campos.

**Esfuerzo**: S (decisión) + M (limpieza masiva de archivos)

---

### TECH-07 · Mezcla de idiomas en mensajes al usuario y logs

**Archivos**: múltiples, principalmente [src/geoecon_metadata/giqmd.py](src/geoecon_metadata/giqmd.py), `checker.py`, `deployer.py`

**Problema**: Los mensajes alternan español e inglés sin criterio. Dificulta hacer `grep` de errores en logs de producción y confunde a colaboradores que solo hablan uno de los dos idiomas.

**Acción**: Adoptar una convención (recomendado: inglés para logs de sistema, español para mensajes al usuario en la CLI) y aplicarla sistemáticamente. No es necesario cambiar todo de una vez — basta con aplicarlo a los mensajes nuevos y corregir los más confusos.

**Esfuerzo**: M (si se hace todo a la vez) / continuo (si se aplica como regla going-forward)

---

### TECH-08 · Bloques de columnas comentados en los YAML de metadatos

**Archivos**: múltiples en `metadata/argentina/` y otros países

**Problema**: Muchos archivos tienen decenas de líneas de columnas comentadas que nunca se van a descomentar. Esto degrada la legibilidad, confunde al lector sobre el estado real del dataset, y hace más difícil el diff en code review.

**Acción**: Política going-forward: si una columna está comentada por más de un sprint, se elimina. Si puede ser necesaria en el futuro, se crea un issue. Aplicar limpieza retroactiva en los archivos más afectados.

**Esfuerzo**: S por archivo, pero son muchos archivos — priorizar por país

---

## P3 — Mejoras de calidad

### TECH-09 · `from functools import cache` importado sin usar

**Archivo**: [src/geoecon_metadata/parsers.py:1](src/geoecon_metadata/parsers.py)

**Acción**: Eliminar el import.

**Esfuerzo**: XS

---

### TECH-10 · Cobertura de tests insuficiente

**Archivos**: [src/tests/](src/tests/)

**Problema**: 5 archivos de test para 40+ módulos, todos de integración. Sin tests unitarios, cualquier refactor de modelos o del parser YAML es ciego.

**Acción** (por orden de ROI):
1. Tests unitarios para validadores de `Source` y `Column` (casos borde: slug inválido, columna sin dimensiones, `default_value` ausente con `use_defaults` activo).
2. Tests para `PersistentAnchorYAML`: anclas cruzadas entre dos archivos, ancla no definida, `push_anchors()` / `pop_anchors()`.
3. Tests de formateo de reportes (plain/html/json) con fixtures fijos.
4. Test de `checker.py` con un mock del processor para desacoplar de BigQuery.

**Esfuerzo**: L (si se quiere cobertura razonable)

---

## Resumen de esfuerzos

| ID | Descripción | Prioridad | Esfuerzo |
|---|---|---|---|
| BUG-01 | `dump_metadata` roto | P0 | XS–M |
| BUG-02 | `report[-1]` IndexError implícito | P0 | S |
| BUG-03 | `pip install` dentro de la app | P0 | XS |
| TECH-01 | Caché sin versionado | P1 | S |
| TECH-02 | `deployed` vs `done` ambiguos | P1 | S+M |
| TECH-03 | Sin `.env.example` | P1 | XS |
| TECH-04 | `update_period` no implementado | P1 | S |
| TECH-05 | Campo `typo` confuso | P2 | M |
| TECH-06 | Campos muertos en YAML | P2 | S+M |
| TECH-07 | Mezcla de idiomas | P2 | M |
| TECH-08 | Columnas comentadas en YAML | P2 | S/archivo |
| TECH-09 | Import sin usar en parsers.py | P3 | XS |
| TECH-10 | Cobertura de tests | P3 | L |

**Leyenda de esfuerzo**: XS < 1h · S 1–4h · M 4h–1 día · L > 1 día
