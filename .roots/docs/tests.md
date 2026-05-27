# Tests — geaiq_mdp

> Relevamiento 27 May 2026. Responde "¿hay tests armados para correr?".

## TL;DR

Hay **5 archivos de test** en `src/tests/`, pero el harness **no está cableado**: `pytest` no está en `pyproject.toml`, no hay `[tool.pytest.ini_options]`, no hay `conftest.py`, y el `Makefile` no tiene target `test`. Para correrlos: `pip install pytest && pytest src/tests/`. 3 de 5 son offline; `test_query.py` requiere GCP.

## Archivos

| Archivo | Cubre | ¿Offline? | Notas |
|---|---|---|---|
| `test_yml_anchor.py` | Persistencia de anclas YAML entre archivos (`PersistentAnchorYAML`) | ✅ sí | núcleo del parser |
| `test_yml_data.py` | Carga de `data/` + resolución de anclas | ✅ sí | |
| `test_yml_parsing.py` | Parse YAML → Pydantic (errores de validación) | ✅ sí | |
| `test_report.py` | Formateo de reportes (HTML/Markdown) | ✅ sí | usa markdown + matplotlib |
| `test_query.py` | Integración: BigQuery dry-run + ejecución | ❌ no | **requiere ADC/GCP project + red** |

## Cómo correrlos

```bash
cd ~/geoecon/geaiq_mdp
pip install pytest            # NO está declarado como dep
pytest src/tests/             # corre todo
pytest src/tests/ -k "not query"   # solo los offline (sin GCP)
pytest src/tests/test_yml_parsing.py -v
```

> Para `test_query.py`: requiere `gcloud auth application-default login` con scope bigquery + proyecto `geoecon-dev`.

## Gaps / deuda (TECH-10 del BACKLOG)

- Cobertura insuficiente: 5 tests para 40+ módulos.
- Sin tests unitarios de los modelos Pydantic (validadores, casos borde).
- Sin mocks de API/BigQuery → los de integración fuerzan credenciales reales.
- Sin `conftest.py` ni fixtures compartidas.
- `pytest` ausente en `pyproject.toml` → agregar a un extra `[project.optional-dependencies].test` + `[tool.pytest.ini_options]` con markers (ej. `requires_gcp`).

## Próximos pasos sugeridos (no hechos)

1. Agregar `pytest` (+ `pytest-mock`) a `pyproject.toml` como extra `test` + config `[tool.pytest.ini_options]` (testpaths=src/tests, markers).
2. Marcar `test_query.py` con `@pytest.mark.requires_gcp` para poder excluirlo offline.
3. Target `make test` (+ `make test-offline`).
4. Sumar tests unitarios de `models/source.py` (validadores, `_migrate_old_format`).
