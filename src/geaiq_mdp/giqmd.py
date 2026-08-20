# Módulos internos de Python
from datetime import datetime, timezone
import logging
import os
import re
import warnings
from io import StringIO
from pathlib import Path
from time import time

from geaiq_mdp.enums import ExitCode
from geaiq_mdp.utils import url_to_logs
from geaiq_mdp.version import get_version_string
from geaiq_mdp.cache import CACHE_PATH
from geaiq_mdp.google_chat import GoogleChatBot
from geaiq_mdp.io_sources import docker_md_yaml, iter_sources
from geaiq_mdp.process_logger import LOG_PATH
from geaiq_mdp.shape import SHAPE_PATH

try:
    # Paquetes de terceros
    import click
    import emoji
    import markdown
    from gspread import SpreadsheetNotFound
    from pydantic import ValidationError

    # Módulos propios
    from geaiq_mdp.cache import invalidate_cache, unlink_cache, cache
    from geaiq_mdp.checker import checker
    from geaiq_mdp.data import load_data
    from geaiq_mdp.deployer import deployer
    from geaiq_mdp.drive import upload_to_drive
    from geaiq_mdp.gcp import setup_ss
    from geaiq_mdp.geoecon_api import GEOECON_API_MAP, GeoEconAPI
    from geaiq_mdp.io_sources import (
        all_md_yaml,
        input_md_yaml,
        commit_md_yaml,
        is_md_yaml,
    )
    from geaiq_mdp.menu import Menu, geoecon_api_url
    from geaiq_mdp.models.geoecon_api import GeoEconAPIModel
    from geaiq_mdp.parsers import parse_menu, parse_metadata
    from geaiq_mdp.persistent_anchor_yaml import PersistentAnchorYAML
    from geaiq_mdp.report import (
        head_plain,
        foot_plain,
        head_markdown,
        foot_markdown,
        head_html,
        menu_scripts_html,
        foot_html,
        format_report_plain,
        format_report_markdown,
        format_report_html,
        format_report_json,
        format_resume_markdown,
        format_resume_plain,
        format_resume_html,
        format_resume_json,
        get_types,
    )
    from geaiq_mdp.spreadsheet import md_import
except ModuleNotFoundError as exc:
    print(
        "Módulo no encontrado. Intentando instalarlo con 'pip install -r requirements.txt'"
    )
    try:
        from pip._internal.cli.main import main as pip_main

        pip_main(["install", "-r", "requirements.txt"])
        print("Instalación completada. Intenta ejecutar el script nuevamente.")
    except Exception as e:
        print(f"Se produjo un error durante la instalación: {e}.")
    exit(1)


def select_files(root, files):
    if root.resolve().drive == "":
        files = (Path(str(f).replace("\\", "/")) for f in files)
    return [root / f for f in files]


logging.basicConfig(level=logging.INFO)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Expresión regular para validar commit hash o referencias válidas
COMMIT_REGEX = re.compile(r"^([0-9a-f]{40}|HEAD|[a-zA-Z0-9._/-]+)$")

CONTEXT_MAP = {
    "none": lambda root, files, _commit: select_files(root, files),
    "file": lambda root, files, _commit: [
        root / f.strip()
        for f in Path(root / files[0]).open("r").readlines()
        if is_md_yaml(root / f.strip())
    ],
    "all": lambda root, _files, _commit: all_md_yaml(root),
    "stdin": lambda root, _files, _commit: input_md_yaml(root),
    "commit": lambda root, _files, _commit: commit_md_yaml(root),
    "docker": lambda root, files, commit: docker_md_yaml(root, commit)
    and select_files(root, files),
}

HEAD_MAP = {
    "plain": head_plain,
    "markdown": head_markdown,
    "html": head_html,
}

FOOT_MAP = {
    "plain": foot_plain,
    "markdown": foot_markdown,
    "html": foot_html,
}

FORMAT_MAP = {
    "plain": format_report_plain,
    "markdown": format_report_markdown,
    "html": format_report_html,
    "json": format_report_json,
}

RESUME_FORMAT_MAP = {
    "plain": format_resume_plain,
    "markdown": format_resume_markdown,
    "html": format_resume_html,
    "json": format_resume_json,
}


DEPLOY_TARGET_MAP = {
    "test": lambda table_name: f"test-{table_name}",
    "dev": lambda table_name: f"dev-{table_name}",
    "prod": lambda table_name: f"{table_name}",
    "local": lambda table_name: f"{table_name}",
}

EMOJI_MAP = {"info": "✅", "ok": "✅", "error": "🛑", "warning": "⚠️"}

MESSAGE_ERROR_MAP = {
    "info": "without errors",
    "ok": "without errors",
    "error": "with errors",
    "warning": "with warnings",
}


def validate_commit(ctx, param, value):
    """Valida que el valor sea un hash de commit o una referencia válida"""
    if value and not COMMIT_REGEX.match(value):
        raise click.BadParameter(
            "Debe ser un hash SHA-1 de 40 caracteres o una referencia válida como HEAD, main, tag, etc."
        )
    return value


@click.group()
@click.option(
    "--context",
    type=click.Choice(CONTEXT_MAP.keys()),
    default="none",
    help="Context work",
)
@click.option(
    "--root",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, readable=True, writable=True
    ),
    default=Path("."),
    help="Working root path",
)
@click.option(
    "--clean-full-cache",
    is_flag=True,
    show_default=True,
    default=False,
    help="Clean full cache.",
)
@click.option(
    "--invalid-cache",
    is_flag=True,
    show_default=True,
    default=False,
    help="Invalid cache.",
)
@click.option(
    "--debug",
    is_flag=True,
    show_default=True,
    default=False,
    help="Enable debug logging.",
)
@click.option(
    "--upload-output",
    is_flag=True,
    show_default=True,
    default=False,
    help="Enable upload output to drive.",
)
@click.option(
    "--target",
    type=click.Choice(GEOECON_API_MAP.keys()),
    default="dev",
    help="Process against dev or prod environments.",
)
@click.option(
    "--commit",
    type=str,
    callback=validate_commit,
    default=None,
    help="Commit name of hash. Used for docker context.",
)
@click.option(
    "--drive-shared-id", default="GeoEcon Repository", help="Shared drive target"
)
@click.option("--drive-path", default="Processing Reports", help="Shared drive target")
@click.option("--chat-webhook", default=os.getenv("CHAT_WEBHOOK"), help="Chat webhook")
@click.pass_context
def cli(
    ctx_,
    context,
    root,
    clean_full_cache,
    invalid_cache,
    debug,
    upload_output,
    commit,
    drive_shared_id,
    drive_path,
    chat_webhook,
    target,
):
    ctx_.ensure_object(dict)
    ctx_.obj["context_name"] = context
    ctx_.obj["root"] = Path(root)
    ctx_.obj["commit"] = commit
    ctx_.obj["context_function"] = lambda files: CONTEXT_MAP[context](
        Path(root), files, commit
    )
    ctx_.obj["upload-output"] = upload_output
    ctx_.obj["drive_shared_id"] = drive_shared_id
    ctx_.obj["drive_path"] = drive_path
    ctx_.obj["target"] = target
    ctx_.obj["start_time"] = time()
    ctx_.obj["gcb"] = (
        GoogleChatBot(chat_webhook) if context == "docker" and chat_webhook else None
    )

    if clean_full_cache:
        unlink_cache()
    if invalid_cache:
        invalidate_cache()

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.info("GeoEcon Metadata CLI version %s", get_version_string())


def worst_report_type(report):
    return max(set(get_types(report)) | {"info"}, key=lambda a: ExitCode[a])


def chat_bot(f):
    def wrapper(ctx_, *args, **kwargs):
        if gcb := ctx_.obj["gcb"]:
            commit = ctx_.obj["commit"]
            message = gcb.send_start_task_message(
                f"🚀 Start task {f.__name__.title()} on batch.",
                url_to_logs(
                    datetime.fromtimestamp(ctx_.obj["start_time"], tz=timezone.utc)
                ),
                [
                    f"https://github.com/GeoEconDev/metadata/blob/{commit}/{file}"
                    for file in kwargs["files"]
                ],
                subtitle="@{email}" + " ".join(f"#{file.name}" for file in kwargs["files"]),
            )
            ctx_.obj["message_thread"] = message["thread"]

        return f(ctx_, *args, **kwargs)

    return wrapper


@cli.result_callback()
@click.pass_context
def finalize(
    ctx,
    results,
    target=None,
    report_file=None,
    context=None,
    chat_webhook=None,
    commit=None,
    **kwargs,
):
    # Esta función se ejecuta después de que todos los subcomandos han terminado
    report_file = ctx.obj.get("report_file", None)
    running_time = time() - ctx.obj["start_time"]

    gcb = ctx.obj["gcb"]

    if report_file and report_file.is_file():
        geoecon_api: GeoEconAPI = GEOECON_API_MAP[target]()

        public_url = geoecon_api.upload_report(
            ctx.invoked_subcommand, "ok" if results == "info" else results, report_file
        )
        public_url = f"{public_url}?st={report_file.stat().st_mtime}"

        if public_url:
            logging.info("Report uploaded to: %s", public_url)
            click.echo(f"Report uploaded to: {public_url}")
            click.launch(public_url)
            if gcb:
                gcb.send_report_message(
                    f"{EMOJI_MAP[results]} {ctx.invoked_subcommand.title()} report generated {MESSAGE_ERROR_MAP[results]}.",
                    f"@{{email}}\n⏱️ Execution time {running_time:.2f} sec.",
                    public_url,
                    [],
                    subtitle=" ".join(f"#{file.name}" for file in ctx.obj["files"]),
                )
        else:
            click.echo("Report not uploaded")

        ctx.exit(
            ExitCode[results] if (results == "error" and context != "docker") else 0
        )


@cli.command()
@click.pass_context
@click.option(
    "--output",
    type=click.File("w", encoding="utf-8"),
    default="-",
    help='Output report file to write the report. Use "-" for stdout.',
)
@click.option(
    "--format",
    type=click.Choice(FORMAT_MAP.keys()),
    default="markdown",
    help="Format output",
)
@click.option(
    "--update",
    is_flag=True,
    show_default=True,
    default=False,
    help="Update data",
)
def init(ctx, output, format, update):
    """Init basic data on database."""
    logging.info(f"Init %s", ctx.obj["context_name"])

    logging.info(f"Reading data")
    reader = PersistentAnchorYAML(typ="safe", pure=True)
    data = load_data(root=ctx.obj["root"], reader=reader)

    logging.info(f"Connecting API")
    target = ctx.obj["target"]
    geoecon_api = GEOECON_API_MAP[target]()

    logging.info(f"Start Init")
    for d in data:
        if isinstance(d, GeoEconAPIModel):
            if d.uuid and update:
                d.update(geoecon_api)
            else:
                logging.info(f"Creating %s: %s", d.__class__.__name__, d.name)
                item = d.create(geoecon_api)
                logging.debug(f"{d.__class__.__name__}: {item.uuid}")
                for sd in item.subitems():
                    sitem = sd.create(geoecon_api)
                    logging.debug(f"subitem:{sd.__class__.__name__}: {sitem.uuid}")

    logging.info(f"Init done")


@cli.command()
@click.pass_context
@click.option(
    "--output",
    type=click.File("w", encoding="utf-8"),
    default="-",
    help='Output report file to write the report. Use "-" for stdout.',
)
@click.option(
    "--format",
    type=click.Choice(FORMAT_MAP.keys()),
    default="markdown",
    help="Format output",
)
@click.option(
    "--only-new",
    is_flag=True,
    show_default=True,
    default=False,
    help="Only load new sources",
)
@click.argument("files", type=Path, nargs=-1)
def check(ctx, output, format, files, only_new):
    """Check yaml metadata files for geoecon."""
    logging.info(f"Checking files on context %s", ctx.obj["context_name"])
    yamls = ctx.obj["context_function"](files)
    full_report = []
    for yaml in yamls:
        logging.info("Checking %s", yaml)
        report = checker([yaml], ctx.obj["target"], only_new, root=ctx.obj["root"])
        full_report.extend(report)
        FORMAT_MAP[format](report, output, "YAML check report")
    RESUME_FORMAT_MAP[format](full_report, output)
    output.close()
    ctx.obj["files"] = files
    ctx.obj["report_file"] = (
        output_path if output and (output_path := Path(output.name)).exists else None
    )

    return worst_report_type(full_report)


@cli.command("deploy")
@click.option(
    "--output",
    type=click.File("w"),
    default="-",
    help='Output report file to write the report. Use "-" for stdout.',
)
@click.option(
    "--format",
    type=click.Choice(FORMAT_MAP.keys()),
    default="markdown",
    help="Format output",
)
@click.argument("files", type=Path, nargs=-1)
@click.option(
    "--only-new",
    is_flag=True,
    show_default=True,
    default=False,
    help="Only load new sources",
)
@click.pass_context
@chat_bot
def deploy(ctx, output, format, files, only_new):
    """Deploy sources content to geoecon environments."""
    target = ctx.obj["target"]
    context_name = ctx.obj["context_name"]
    click.echo(f"Deploy context {context_name} on {target}")

    if not files:
        click.echo(f"No input files.")
        logging.error(f"No input files.")
        return "error"

    yamls = ctx.obj["context_function"](files)

    if not yamls:
        click.echo(f"No yaml files found. Input files: {files}")
        logging.error("No yaml files. Input files: %s", files)
        return "error"

    report = deployer(yamls, ctx.obj["target"], only_new, root=ctx.obj["root"])

    FORMAT_MAP[format](report, output, "Deploy report")
    output.close()
    ctx.obj["report_file"] = (
        output_path if output and (output_path := Path(output.name)).exists else None
    )
    ctx.obj["files"] = files

    if report:
        for r in report:
            r_m = (
                r["report"]
                if r["report"]
                else [{"type": "warning", "message": "No messages"}]
            )
            for r in r_m:
                click.echo(f"{r['type']}:{r['message']}")

        return worst_report_type(report)
    else:
        click.echo(f"No report. No yaml files?")
        return "error"


@cli.command("import")
@click.option(
    "--name", default="metadatos", help="Spreadsheet name of metadata spreadsheet"
)
@click.option("--url", help="URL to metadata spreadsheet")
@click.option("--key", help="ID key to metadata spreadsheet")
def import_(url, name, key):
    """Import files from spreadsheet."""
    click.echo("Import from spreadsheets")

    gc, user = setup_ss()

    try:
        spreadsheet = (
            gc.open_by_url(url)
            if url
            else gc.open_by_key(key) if key else gc.open(name)
        )
    except SpreadsheetNotFound as exc:
        click.echo("Spreadsheet not found")
        return
    except PermissionError as exc:
        click.echo(f"User {user} can't read Spreadsheet")
        return

    md_import(spreadsheet)


@cli.group()
def menu():
    """Read menu files."""
    pass


@menu.command
@click.option(
    "--output",
    type=click.File("w"),
    default="-",
    help='Output file to write the report. Use "-" for stdout (default).',
)
@click.option(
    "--format",
    type=click.Choice(FORMAT_MAP.keys()),
    default="markdown",
    help="Format output",
)
@click.argument("metadata", type=Path, nargs=-1)
@click.pass_context
def check(ctx, output, format, metadata):
    """Check menu files."""
    geoecon_api: GeoEconAPI = GEOECON_API_MAP[ctx.obj["target"]]()
    # El reporte se arma SIEMPRE en memoria. Antes, con `--format markdown`, era
    # `report = output`, y eso rompía de dos maneras a la vez:
    #   1. `output.write(report.getvalue())` reventaba con
    #      `AttributeError: '…' object has no attribute 'getvalue'`, porque `report`
    #      era el propio archivo. El único formato utilizable quedaba `html`.
    #   2. Aun sin eso, `menu.process(report)` ya había escrito el cuerpo directo en
    #      el archivo, así que el HEAD se agregaba DESPUÉS del cuerpo.
    # Con StringIO el orden queda head → body → foot para los dos formatos.
    report = StringIO()

    menu = Menu(geoecon_api)

    click.echo("Load menu")
    menu.load(metadata=metadata, root=ctx.obj["root"])

    click.echo("Retrieve data")
    menu.retrieve()

    click.echo("Processing menu")
    menu.process(report)

    # El head del reporte del menú lleva ADEMÁS el JS del formulario, inline.
    # Sin él, `postToGeoEcon` queda indefinida y el botón "Agregar/Actualizar
    # Menú" no hace nada: el reporte se ve bien y no escribe una sola fila en
    # `ui.t_menu` — que es por qué el catálogo quedó congelado desde julio.
    # Sólo aplica al formato html (los otros no tienen dónde poner un <script>).
    extra_head = menu_scripts_html(geoecon_api_url) if format == "html" else ""
    output.write(
        HEAD_MAP[format](
            title=f"Menu processing with {metadata}", extra_head=extra_head
        )
    )
    if format == "html":
        output.write(markdown.markdown(report.getvalue(), extensions=["tables"]))
    else:
        output.write(report.getvalue())
    output.write(FOOT_MAP[format]())

    click.echo(f"Looks good. Check report file '{output.name}'.")

    ctx.obj["report_file"] = (
        output_path if output and (output_path := Path(output.name)).exists else None
    )

    return worst_report_type(report)


@cli.group()
def tags():
    """Manage tags."""
    pass


@tags.command
@click.option(
    "--output",
    type=click.File("w"),
    default="-",
    help='Output file to write the report. Use "-" for stdout (default).',
)
@click.option(
    "--format",
    type=click.Choice(FORMAT_MAP.keys()),
    default="markdown",
    help="Format output",
)
@click.option(
    "--no-upload",
    is_flag=True,
    show_default=True,
    default=False,
    help="Only load new sources",
)
@click.pass_context
def upload(ctx, output, format, no_upload):
    """Check menu files."""
    geoecon_api: GeoEconAPI = GEOECON_API_MAP[ctx.obj["target"]]()
    # Mismo caso que en `menu check`: con `--format markdown`, `report = output`
    # hacía reventar `report.getvalue()` y además metía el HEAD después del cuerpo.
    report = StringIO()

    menu = Menu(geoecon_api)

    click.echo("Load menu")
    menu.load()

    click.echo("Uploading tags from menu")
    menu.upload_tags(report, no_upload=no_upload)

    output.write(HEAD_MAP[format](title=f"Tags uploading"))
    if format == "html":
        md = markdown.Markdown()
        output.write(md.convert(report.getvalue()))
    else:
        output.write(report.getvalue())
    output.write(FOOT_MAP[format]())

    click.echo(f"Looks good. Check report file '{output.name}'.")

    ctx.obj["report_file"] = (
        output_path if output and (output_path := Path(output.name)).exists else None
    )

    return "ok"


@cli.command()
@click.argument("files", type=Path, nargs=-1)
@click.pass_context
def reset(ctx, files):
    report = []
    yamls = ctx.obj["context_function"](files)
    reader = PersistentAnchorYAML(typ="safe", pure=True)
    load_data(root=ctx.obj["root"], reader=reader)

    for src in iter_sources(yamls, report, reader=reader):
        click.echo(f"🧹💾 - {src.slug}")
        for f in CACHE_PATH.glob(f"*{src.slug}*"):
            click.echo(f"🗑️ - {f}")
            f.unlink()

        click.echo(f"🧹📖 - {src.slug}")
        for f in LOG_PATH.glob(f"*{src.slug}*"):
            click.echo(f"🗑️ - {f}")
            f.unlink()

        click.echo(f"🧹🗺️ - {src.slug}")
        for d in SHAPE_PATH.glob(f"*{src.slug}*"):
            for f in d.iterdir():
                click.echo(f"🗑️ - {f}")
                f.unlink()

    click.echo("Done")


if __name__ == "__main__":
    try:
        cli()
    except ValidationError as err:
        click.echo(click.style("¡Alto ahí!", fg="red"))
        click.echo(
            emoji.emojize(
                ":warning: Se ha detectado un error al procesar el archivo :warning:"
            )
        )
        click.echo(
            emoji.emojize("Parece que hay un problema con los metadatos. :file_folder:")
        )
        click.echo(
            emoji.emojize(
                "Por favor, verifica que los metadatos estén completos y sean correctos."
            )
        )
        click.echo()
        click.echo(click.style("Error detallado:", fg="yellow"))
        click.echo(err)
