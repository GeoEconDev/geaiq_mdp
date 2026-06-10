# Tests — geaiq_mdp

> Relevamiento 27 May 2026; actualizado 9 Jun 2026 (a15 migró a pytest).

## TL;DR

Hay **5 archivos de test** en `src/tests/`. Desde **a15 el harness está cableado**: extra
`[project.optional-dependencies].test = ["pytest", "pandas"]` + `[tool.pytest.ini_options]`
(`testpaths=["src/tests"]`, `pythonpath=["src"]`) en `pyproject.toml`, y descubrimiento configurado en
`.vscode/settings.json`. Los scripts viejos con `if __name__ == "__main__"`/prints se convirtieron a tests
reales (assertions, `pytest.raises`, fixture `tmp_path`). Correr: `pip install -e .[test] && pytest`.
`test_query.py` quedó con `@pytest.mark.skip` (requiere credenciales BigQuery). Falta aún: markers propios
(ej. `requires_gcp`), `conftest.py`/fixtures compartidas, target `make test` y subir cobertura (TECH-10).

## Archivos

| Archivo | Cubre | ¿Offline? | Notas |
|---|---|---|---|
| `test_yml_anchor.py` | Persistencia de anclas YAML entre archivos (`PersistentAnchorYAML`) | ✅ sí | núcleo del parser |
| `test_yml_data.py` | Carga de `data/` + resolución de anclas | ✅ sí | |
| `test_yml_parsing.py` | Parse YAML → Pydantic (errores de validación) | ✅ sí | |
| `test_report.py` | Formateo de reportes (HTML/Markdown) | ✅ sí | usa markdown + matplotlib |
| `test_query.py` | Integración: BigQuery dry-run + ejecución | ❌ no | `@pytest.mark.skip` (requiere ADC/GCP + red) |

## Cómo correrlos

```bash
pip install -e .[test]        # pytest + pandas (extra declarado, a15)
pytest                        # usa testpaths=src/tests de pyproject.toml
pytest -k "not query"         # offline
pytest src/tests/test_yml_parsing.py -v
```

> `test_query.py` está `skip` por defecto; quitar el marker y autenticar (`gcloud auth application-default login`, scope bigquery, proyecto `geoecon-dev`) para correrlo.

## Gaps / deuda (TECH-10 del BACKLOG)

- Cobertura insuficiente: 5 tests para 40+ módulos.
- Sin tests unitarios de los modelos Pydantic (validadores, casos borde) ni de los adapters Airflow (`airflow_*.py`).
- Sin mocks de API/BigQuery/Hooks → los de integración fuerzan credenciales reales.
- Sin `conftest.py` ni fixtures compartidas; sin markers propios (ej. `requires_gcp` en vez de `skip`).

## Próximos pasos sugeridos (no hechos)

1. Reemplazar el `@pytest.mark.skip` de `test_query.py` por `@pytest.mark.requires_gcp` para excluirlo selectivamente.
2. Target `make test` (+ `make test-offline`).
3. Sumar tests unitarios de `models/source.py` (validadores, `_migrate_old_format`) y de `airflow_utils.resolve_conn_id`.
4. Agregar `conftest.py` con fixtures compartidas y `pytest-mock` para mockear Hooks/clientes.
