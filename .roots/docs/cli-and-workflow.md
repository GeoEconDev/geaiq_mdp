# CLI `giqmd` + flujo de trabajo

> Referencia operativa. Ver `architecture.md` para el interno.

## Instalación

```bash
pip install -e .            # Python ≥ 3.11
# o solo deps: pip install -r requirements.txt
```

## Config GCP (una vez)

```bash
gcloud config set project geoecon-dev
gcloud services enable sheets.googleapis.com drive.googleapis.com bigquery.googleapis.com
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/bigquery
```

Env vars: `GOOGLE_APPLICATION_CREDENTIALS` (JSON service account, alt a ADC) · `CHAT_WEBHOOK` (Google Chat) · `GIT_TOKEN` + `METADATA_GIT_REPO` + `GIT_COMMIT` (solo `--context docker`) · `METADATA_DIR` (raíz, default `.`).

## Lifecycle de una source

```
draft → ready → (giqmd check) → valid → (giqmd deploy) → deployed/done
                                                       ↘ error / failed
```
1. Crear `metadata/{país}/{slug}.yml` con `status: draft`.
2. Completar campos → `status: ready`.
3. `giqmd check <archivo>` → si pasa, poner `status: valid`.
4. `giqmd --target dev deploy <archivo>` → `deployed`. Repetir con `--target prod`.

## Opciones globales

```
--context [none|file|all|stdin|commit|docker]   selección de archivos (default none)
--root PATH                                      raíz del repo (default .)
--target [dev|prod|test|local]                   entorno destino (default dev)
--commit TEXT                                    ref git (con --context docker)
--clean-full-cache | --invalid-cache             cache ~/.geoecon-cache/
--upload-output                                  sube reporte a Drive/GCS
--debug                                          logging DEBUG
--chat-webhook URL                               webhook Google Chat
```

## Comandos

| Comando | Descripción |
|---|---|
| `init [--update]` | Inicializa datos base (scales, periods, attributes) en la API. 1 vez por entorno. |
| `check` | Valida archivos `ready` (dry-run BQ / descarga shape). `--format html\|md\|json`, `--output FILE`, `--only-new`. |
| `deploy` | Despliega sources `valid` a la API + warehouse. Mismas flags de formato. |
| `reset FILES` | Limpia caché, logs y shapefiles de las fuentes. |
| `import SPREADSHEET_ID` | Importa metadatos desde Google Sheets. |
| `menu check` | Valida archivos de menú. |
| `tags upload` | Sube tags del menú a la API (`ui/tags`). |

### Ejemplos

```bash
giqmd check metadata/argentina/arg2023-prestamos-adm01.yml
giqmd --context commit check                        # archivos modificados en el último commit
giqmd --target dev deploy --format html --output report.html metadata/argentina/mi_fuente.yml
giqmd --target prod deploy metadata/argentina/mi_fuente.yml
giqmd reset metadata/argentina/mi_fuente.yml
giqmd --target dev init                             # solo 1 vez por entorno
```

## Makefile

| Target | Acción |
|---|---|
| `make sync` | Sincronización bidireccional develop ↔ ramas de colaboradores. |
| `make sync-from-develop` / `make sync-develop` | Un sentido cada uno. |
| `make clean-cache` / `clean-reports` / `clean-logs` | Limpieza local. |
| `make show-status` | `grep -r "status:" metadata/` (vive en el repo de datos). |
| `make check-metadata file=...` / `deploy-metadata file=...` / `reset-metadata file=...` | Ejecuta el comando en **Cloud Run Job** `metadata` (geoecon-dev, us-central1). |

## Branches

`develop` (integración) + 1 rama por colaborador: `cr` (Cristian Rocha), `jp`, `jm`, `vs`, `na`, `fc`. Merge sin PR, automatizado con `make sync`. (Evita conflictos YAML entre analistas que tocan distintos países.)
