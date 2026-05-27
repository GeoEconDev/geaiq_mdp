# geaiq_mdp – Backlog

> Deuda técnica + tareas. Portado del `BACKLOG.md` del repo + relevamiento `.roots` (27 May 2026). Verificar contra `BACKLOG.md` (fuente viva del equipo) antes de tomar uno.

---

## 🐞 Bugs

- [ ] **BUG-01 — `dump_metadata()` roto** (`parsers.py:~34`): referencia `reader`/`filename` sin definirlos → `NameError` si se llama. Nunca se ejecuta hoy.
- [ ] **BUG-02 — `report[-1]` invariante implícita** (`checker.py:~24`): asume que `iter_sources()` insertó el elemento antes del body → `IndexError` si se rompe. Hacer explícito o refactorizar.
- [ ] **BUG-03 — `pip install` interno** (`giqmd.py:~63-74`): bloque `except ModuleNotFoundError` invoca pip; frágil, silencia el error real, instala versiones incorrectas en Docker (que ya trae deps). Reemplazar por error claro.

## 🔧 Deuda técnica

- [ ] **TECH-01 — Cache sin versionado de schema** (`cache.py`): unpickle falla en silencio tras cambiar modelos Pydantic → `AttributeError` críptico. Versionar el cache o invalidar por hash del modelo.
- [ ] **TECH-02 — `status: deployed` vs `done` ambiguos**: ambos en `SourceStatus`, sin doc clara, uso inconsistente en los YAML. Definir semántica.
- [ ] **TECH-04 — `update_period()` no implementado** (`geoecon_api.py`).
- [ ] **TECH-05 — `typo` confuso**: en `ObservableScale`/`Class_` significa "tipo". Alias `kind` con fallback `typo`.
- [ ] **TECH-06 — Campos muertos en YAML**: `state`, `source_message` (vacíos), `old_source` (queries obsoletas, peligroso). Limpiar.
- [ ] **TECH-07 — Idioma mezclado es/en** en logs/CLI → dificulta grep en prod. Unificar.
- [ ] **TECH-10 — Tests insuficientes**: ver `docs/tests.md`. Agregar pytest a pyproject + config + markers + tests unitarios de modelos.

## 🌱 Mejoras / pendientes del ecosistema

- [ ] **Implementar `PostgreSQLSourceProcessor`** (`processors.py`, hoy `NotImplementedError`): es la persistencia-a-postgres que pide el repo padre (`geoecon_map` § design-data-abstraction). Habilita `source.platform: postgresql`.
- [ ] **Extender `MeasurementUnit`** con unidades faltantes (CO2eq, Kelvin/°C explícito, µg/m³) — junta con la tarea de unidades del repo padre (el card mostraba "0 hab." para emisiones).
- [ ] **Cablear el harness de tests** (pytest en pyproject + conftest + `make test`). Ver `docs/tests.md § Próximos pasos`.

---

## En progreso

_(ninguna — sesión 27 May fue bootstrap del `.roots/`, sin código)_
