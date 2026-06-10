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
- [ ] **TECH-10 — Cobertura de tests insuficiente**: el harness ya existe (pytest en pyproject + config, a15). Resta agregar markers y tests unitarios de modelos/adapters. Ver `docs/tests.md`.

## 🌱 Mejoras / pendientes del ecosistema

- [x] **Implementar fuente PostgreSQL** — hecho en a11/a13 vía `AirflowPostgreSQLProcessor` (`airflow_pg.py`, `PostgresHook`, `EXPLAIN` como dry-run). Habilita `source.platform: postgresql` cuando corre en Airflow. NO hay cliente directo Postgres (en backend `gcp`/directo sigue dando `NotImplementedError`) — pendiente solo si se necesita fuera de Airflow.
- [ ] **Extender `MeasurementUnit`** con unidades faltantes (CO2eq, Kelvin/°C explícito, µg/m³) — junta con la tarea de unidades del repo padre (el card mostraba "0 hab." para emisiones).
- [x] **Cablear el harness de tests** — hecho en a15: extra `[test]` + `[tool.pytest.ini_options]` en `pyproject.toml`, tests migrados a pytest (assertions/fixtures), descubrimiento en VS Code. Resta: subir cobertura (TECH-10) y `make test`.

---

## En progreso

_(ninguna — sesión 27 May fue bootstrap del `.roots/`, sin código)_
