import os
from pathlib import Path
import yaml
import git
import fileinput
import pydantic_core
import ruamel.yaml
import logging
import requests
import tarfile
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from .parsers import parse_metadata
from .persistent_anchor_yaml import PersistentAnchorYAML


def load_yaml_file(file, reader=None):
    if not file.exists():
        logging.error("File not found: %s", str(file))
        yield None, [{"type": "error", "message": f"File not found"}]
        return

    with file.open("r", encoding="utf8") as f:
        try:
            for source in parse_metadata(f, reader=reader):
                yield source, []
        except pydantic_core._pydantic_core.ValidationError as exc:
            logging.error(f"ValidationError:YAML no válido: %s", exc)
            yield None, [
                {"type": "error", "message": error_item["msg"], "details": {
                    'Expected type': error_item["type"],
                    'Input value': 'None' if (input := error_item["input"]) is None else input,
                    "Location": "/".join([str(i) for i in error_item["loc"]]),
                    "More information": error_item["url"]
                }}
                for error_item in exc.errors()
            ]
        except ruamel.yaml.error.MarkedYAMLError as exc:
            logging.error(f"MarkedYAMLError:YAML no válido: %s", exc)
            yield None, [
                {
                    "type": "error",
                    "message": exc.problem,
                    "line": exc.problem_mark.line,
                    "column": exc.problem_mark.column,
                }
            ]
        except yaml.YAMLError as exc:
            logging.error(f"YAMLError:YAML no válido: %s", exc)
            yield None, [{"type": "error", "message": f"YAML no válido: {exc}"}]


def is_md_yaml(file):
    return file.match("metadata/**/*.yml") or file.match("metadata/**/*.yaml")


def all_md_yaml(root):
    return iter(root.glob("metadata/**/*.yml"))


def input_md_yaml(root):
    return iter(
        root / f.strip()
        for f in fileinput.input(encoding="utf8")
        if is_md_yaml(root / f.strip())
    )


def commit_md_yaml(root):
    repo = git.Repo(root)
    last_commit = repo.head.commit
    return iter(
        root / f.strip()
        for f, v in last_commit.stats.files.items()
        if is_md_yaml(root / f.strip()) and v["deletions"] != v["lines"]
    )


def iter_sources(file_iter, report, expected_status=None, reader=None):
    for file in file_iter:
        base_report = {"file": str(file), "sources": []}
        report.append({**base_report})
        source = None
        for source, source_report in load_yaml_file(file, reader=reader):
            report[-1]["status"] = expected_status
            report[-1]["report"] = source_report
            if source:
                if (expected_status is None) or (
                    source.status == expected_status and not source.disabled
                ):
                    yield source
                else:
                    logging.info(
                        "Ignoring source ´%s´ by status ´%s´, expected ´%s´",
                        source.slug,
                        source.status.value,
                        expected_status.value,
                    )
                    report[-1]["sources"].append(
                        {
                            source.slug: [
                                {
                                    "type": "warning",
                                    "message": f"Ignored by status ´{source.status.value}´. Expected ´{expected_status.value}´.",
                                }
                            ]
                        }
                    )

            if isinstance(reader, PersistentAnchorYAML):
                reader.pop_anchors()


def delete_files_in_directory(directory: Path):
    """
    Elimina todos los archivos y directorios dentro del directorio especificado.

    Parámetros:
        directory (Path): Ruta del directorio donde se eliminarán los archivos.
    """
    if directory.is_dir():
        for file in directory.iterdir():
            if file.is_file():
                file.unlink()  # Elimina el archivo
            else:
                delete_files_in_directory(file)
        logging.info("Se eliminaron todos los archivos en: %s", directory)
    else:
        logging.error("No es un directorio válido: %s", directory)


def download_commit(repo_url, commit_hash, target_dir, token):
    """
    Descarga y extrae un commit específico de un repositorio GitHub.

    Parámetros:
        repo_url (str): URL del repositorio en GitHub (ej. "https://github.com/GeoEconDev/metadata").
        commit_hash (str): Hash del commit a descargar.
        target_dir (str): Directorio donde se extraerá el contenido.
        login (str): Usuario de GitHub.
        token (str): Token de autenticación.

    Retorna:
        bool: True si la descarga y extracción fueron exitosas, False en caso de error.
    """
    logging.info("Download commit %s.", commit_hash)

    # Construir la URL de descarga
    tar_url = f"{repo_url}/tarball/{commit_hash}"
    tar_filename = f"{commit_hash}.tar.gz"

    # Datos de autenticación
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Realizar la solicitud GET sin verificar el certificado SSL
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    response = requests.get(tar_url, headers=headers, verify=False)

    if response.status_code == 200:
        # Guardar el archivo comprimido
        with open(tar_filename, "wb") as f:
            f.write(response.content)
        logging.info("Descarga completa: %s", tar_filename)

        # Crear el directorio de extracción si no existe
        target_dir.mkdir(exist_ok=True)
        delete_files_in_directory(target_dir / "data")
        delete_files_in_directory(target_dir / "menu")
        delete_files_in_directory(target_dir / "metadata")

        # Extraer el contenido del archivo .tar.gz
        with tarfile.open(tar_filename, "r:gz") as tar:
            members = tar.getmembers()

            # Obtener el nombre del directorio raíz (primer nivel dentro del tar)
            root_dir = members[0].name.split("/")[0]

            for member in members:
                if (
                    member.name.startswith(f"{root_dir}/data/")
                    or member.name.startswith(f"{root_dir}/menu/")
                    or member.name.startswith(f"{root_dir}/metadata/")
                ):
                    # Ajustar la ruta de extracción para eliminar el subdirectorio principal
                    member.path = member.path[len(root_dir) + 1 :]
                    tar.extract(member, path=target_dir)

        logging.info("Archivos extraídos en: %s", target_dir)

        # Eliminar el archivo comprimido después de extraerlo
        os.remove(tar_filename)
        return True
    else:
        logging.error(
            f"Error en la descarga: %s, %s", response.status_code, response.text
        )
        return False


def docker_md_yaml(root: Path, commit: str | None):
    """Prepara el contexto de trabajo para una imagen de docker"""
    COMMIT_HASH = commit or os.getenv("GIT_COMMIT", None)
    REPO_URL = os.getenv(
        "METADATA_GIT_REPO", "https://api.github.com/repos/GeoEconDev/metadata"
    )
    TARGET_DIR = root or Path(os.getenv("METADATA_DIR", "/tmp/geaiq_mdp"))
    TOKEN = os.getenv("GIT_TOKEN", None)

    errors = []

    if COMMIT_HASH is None:
        errors.append("- GIT_COMMIT no está definido")

    if REPO_URL is None:
        errors.append("- METADATA_GIT_REPO no está definido")

    if TARGET_DIR is None:
        errors.append("- METADATA_DIR no está definido")

    if TOKEN is None:
        errors.append("- GIT_TOKEN no está definido")

    if errors:
        print(
            "\nPlease setup following environment variables for docker context.\n\n"
            + "\n".join(errors)
        )
        exit(-1)

    if download_commit(REPO_URL, COMMIT_HASH, TARGET_DIR, TOKEN):
        return True
    else:
        print("Can't download commit. Check environment variables.")
        return False
