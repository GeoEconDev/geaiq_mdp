import base64
from datetime import datetime
import json
import os
from pathlib import Path
import textwrap
import time
import pandas as pd
import geopandas as gpd
import numpy as np
from pydantic import BaseModel
from io import StringIO, BytesIO
import markdown
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt 

from geoecon_metadata.utils import memory_time_logger
from geoecon_metadata.version import get_version_string

TYPE_MESSAGE_STYLE_MAP = {
    "info": "color:darkgray",
    "warning": "color:orange",
    "error": "color:red",
    "missing": "color:red",
    "string_type": "color:red",
    "list_type": "color:red",
}


DEFAULT_MAX_LENGTH = 20
DEFAULT_CHUNK_SIZE = 200


HTML_HEADER = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script>
        MathJax = {{
        tex: {{
            inlineMath: [['$', '$'], ['\\(', '\\)']]
        }}
        }};
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-sql.min.js"></script>
    <script type="text/javascript" src="/statics/geoecon_api_menu.js?st={st}"></script>
    <link rel="stylesheet" href="/statics/styles.css?st={st}">
</head>
<body>
"""

HTML_FOOTER = """
<div class="footer">
    <div class="buttons">
    {buttons}
    </div>
</div>
</body>
</html>
"""


def head_plain(title):
    return ""


def foot_plain():
    return ""


def head_markdown(title):
    return f"# {title}"


def foot_markdown():
    return ""


def head_html(title):
    return HTML_HEADER.format(title=title, st=time.time())


def foot_html(update_topics=True, view_dashboard=True):
    st = time.time()
    buttons = []
    button_html = "<a href='{}' style='width: 80%'>{}</a>"
    if update_topics:
        buttons.append(
            (
                f"https://mapdev.geoecon.info/query.php?type=topic&topic_ids=all&_reset_=1&q={st}",
                "Actualizar TOPICS UI",
            )
        )
    if view_dashboard:
        buttons.append(
            (
                f"https://mapdev.geoecon.info/demo.php?mode=full&reset=1&q={st}",
                "Ver en Dashboard GeoEcon",
            )
        )
    return HTML_FOOTER.format(
        st=st, buttons="<br/>".join(button_html.format(*b) for b in buttons)
    )


def get_type_message(report_item):
    report_type = report_item.get("type", "Unknown type")
    message = report_item.get("message") or report_item.get("msg") or "No message"
    if "details" in report_item:
        summary = message
        details = report_item["details"]
    else:
        summary, details_str = (
            message.split(":", 1) if ":" in message else (message, "")
        )
        details = [details_str] if details_str else []
    if "loc" in report_item:
        loc = "/".join(str(i) for i in report_item.get("loc", []))
        summary = f"[{loc}] {summary}"
    elif "line" in report_item:
        line, col = report_item["line"], report_item["column"]
        summary = f"[{line}:{col}] {summary}"
    return report_type, summary, details


def iter_reports(reports):
    if isinstance(reports, list):
        for report_item in reports:
            yield get_type_message(report_item)
    if isinstance(reports, dict):
        yield get_type_message(reports)


def format_report_plain(check_result, output=None, title=None):
    for item in check_result:
        file = item.get("file", "Unknown file").strip()
        sources = item.get("sources", [])
        report = item.get("report", [])

        print(f"{title or 'YAML Report'}", file=output)
        print(f"File: {file}", file=output)
        print(f"Date: {datetime.datetime.now()}", file=output)

        if sources:
            print("Sources:", file=output)
            for source in sources:
                for key, reports in source.items():
                    print(f"  {key}:", file=output)
                    for report_type, summary, details in iter_reports(reports):
                        details_str = "\n - ".join(details)
                        print(
                            f"    [{report_type}] {summary}\n{details_str}", file=output
                        )
        else:
            print("Sources: None", file=output)

        if report:
            print("Report:", file=output)
            for report_type, summary, details in iter_reports(report):
                details_str = "\n - ".join(details)
                print(f"    [{report_type}] {summary}\n{details_str}", file=output)
        else:
            print("Report: None", file=output)

        print("", file=output)  # Add a blank line for separation


def format_report_markdown(check_result, output=None, title=None):
    print(f"## {title or 'YAML Report'}", file=output)
    print(f"{datetime.now()}", file=output)

    if not check_result:
        print(" - No files to check", file=output)
        return

    for item in check_result:
        format_message_markdown(item, output)

    print(
        f"\n\n<sub><sup>GeoEcon Metadata CLI version {get_version_string()}</sup></sub>"
    )


def format_report_html(check_result, output=None, title=None):
    with StringIO() as md_output:
        format_report_markdown(check_result, md_output)
        html = markdown.markdown(
            md_output.getvalue(), extensions=["tables", "fenced_code"]
        )

    try:
        title_final = f"{title or ''}{Path(check_result[0]['file']).name}"
    except:
        title_final = title or "Report"

    output.write(head_html(title_final))
    output.write(html)
    output.write(foot_html(update_topics=False, view_dashboard=False))


def format_report_json(check_result, output=None, title=None):
    json.dump(check_result, output)


def format_detail_md(detail, l=0, prefix=""):
    indent = f"{prefix}{'  '*l}" if (l > 0) else ""
    if isinstance(detail, (bool, int, float, str, np.number)):
        return f"{detail}"
    elif isinstance(detail, tuple) and len(detail) == 2:
        title, description = detail
        description = format_detail_md(description, l, prefix)
        return f"**{title}**: {description}"
    elif isinstance(detail, list) and detail:
        limit = 100
        text = "".join(
            [
                f"\n{indent}- {format_detail_md(d, l+1, prefix)}"
                for i, d in enumerate(detail[:limit])
                if d is not None
            ]
        )
        if len(detail) > 100:
            text = text + f"\n{indent}{len(detail)-limit} more..."
        return text
    elif isinstance(detail, dict):
        return format_detail_md(list(detail.items()), l, prefix)
    elif isinstance(detail, tuple) and len(detail) == 1:
        return format_detail_md(detail[0], l, prefix)
    elif isinstance(detail, tuple) and len(detail) > 2:
        return format_detail_md(list(detail), l, prefix)
    elif isinstance(detail, pd.DataFrame):
        return dump_df(detail)
    elif isinstance(detail, pd.Series):
        return format_detail_md(detail.reset_index(), l, prefix)
    elif isinstance(detail, BaseModel):
        try:
            return f"**{type(detail).__name__}**\n{format_detail_md(detail.model_dump(warnings=False), l, prefix)}"
        except ValueError as err:
            return f"\n\n**Reporting issue**\n\n    - Class:{type(detail).__name__}\n    - uuid={detail.uuid}\n    - name={detail.name}\n\n{err}\n"
    elif detail is None:
        return "No details."
    else:
        pass

    return ""


def format_message_markdown(messages, output=None):
    file = messages.get("file", "Unknown file")
    sources = messages.get("sources", [])
    report = messages.get("report", [])

    print(f"### File: `{file}`", file=output)

    if sources:
        print("#### Sources", file=output)
        for source in sources:
            print("\n---\n", file=output)
            for key, reports in source.items():
                print(f"##### {key}", file=output)
                for report_type, summary, details in iter_reports(reports):
                    details_str = format_detail_md(details)
                    print(
                        f"""
###### [{report_type.upper()}] {summary}
    {details_str}
                        """,
                        file=output,
                    )
            print("\n---\n", file=output)
    else:
        print("#### Sources: None", file=output)

    if report:
        print("#### Global Report", file=output)
        for report_type, summary, details in iter_reports(report):
            details_str = format_detail_md(details)
            print(
                f"""
##### [{report_type.upper()}] {summary}
    {details_str}
                """,
                file=output,
            )
    else:
        print("#### Global Report: None", file=output)

    print("---", file=output)  # Add a blank line for separation


def resume(report):
    rows = []
    for s in report:
        file = s["file"]
        for l in s["sources"]:
            for source_name, messages in l.items():
                rows.extend(
                    [
                        (Path(file).name, source_name, m["type"], m["message"])
                        for m in messages
                        if m["type"] != "info"
                    ]
                )
    return pd.DataFrame(rows, columns=["file", "source", "type", "message"])


def format_resume_plain(check_result, output=None):
    re = resume(check_result)
    print("### Report resume", file=output)

    print(re.value_counts(["type", "message"]).reset_index(), file=output)
    print("***", file=output)

    print(re.value_counts(["source", "type"]).reset_index(), file=output)

    print("***", file=output)  # Add a blank line for separation
    print("---", file=output)  # Add a blank line for separation


def format_resume_markdown(check_result, output=None):
    re = resume(check_result)
    now = datetime.now()
    if re.empty:
        print("### No resume", file=output)

    else:
        print("### Report resume\n", file=output)
        print("#### Cantidad de mensajes por tipo\n", file=output)
        print(
            re.value_counts(["type", "message"]).reset_index().to_markdown(),
            file=output,
        )
        print("\n\n", file=output)
        print("#### Cantidad de tipo de mensajes por fuente de datos\n", file=output)
        print(
            re.value_counts(["source", "type"]).reset_index().to_markdown(), file=output
        )
        print("\n\n", file=output)

    print("\n---\n", file=output)  # Add a blank line for separation

    print(f"\n\n[{now:%d-%m-%Y %H:%M:%S}]", file=output)


def format_resume_html(check_result, output=None):
    with StringIO() as md_output:
        format_resume_markdown(check_result, md_output)
        html = markdown.markdown(md_output.getvalue(), extensions=["tables"])
    output.write(html)


def format_resume_json(check_result, output=None):
    # json.dump(check_result, output)
    pass


def get_types(check_result):
    def get_from_message(message):
        if message and isinstance(message, dict):
            yield message["type"]
        elif message and isinstance(message, list):
            for item in message:
                yield from get_from_message(item)

    for item in check_result:
        messages = [item.get("report", {})] + [
            ms for x in item.get("sources", []) for y in x.values() for ms in y
        ]
        for report_item in messages:
            yield from get_from_message(report_item)


def has_type(check_result, types):
    for item in check_result:
        report = item.get("report", [])
        if isinstance(report, list):
            for report_item in report:
                if report_item.get("type") in types:
                    return True
        elif isinstance(report, dict):
            if report.get("type") in types:
                return True
    return False


def has_error(check_result, types=[]):
    return has_type(check_result, types + ["model_type", "error"])


def has_warning(check_result, types=[]):
    return has_type(check_result, types + ["warning"])


def truncar_texto(texto, max_length=20):
    if isinstance(texto, str) and len(texto) > max_length:
        return textwrap.shorten(texto, width=max_length, placeholder="...")
    return texto


@memory_time_logger
def truncar_tabla(df, max_length=None, chunk_size=None):
    """
    Procesa un DataFrame en chunks, truncando el texto en cada celda.

    Args:
      df: El DataFrame de Pandas a procesar.
      max_length: La longitud máxima del texto truncado.
      chunk_size: El tamaño de cada lote.

    Returns:
      Un nuevo DataFrame con el texto truncado.
    """
    max_length = (
        max_length if max_length else int(os.getenv("MAX_LENGTH", DEFAULT_MAX_LENGTH))
    )
    chunk_size = (
        chunk_size if chunk_size else int(os.getenv("CHUNK_SIZE", DEFAULT_CHUNK_SIZE))
    )
    resultados = []
    n_chunks = len(df.index) // chunk_size + (len(df.index) % chunk_size > 0)

    for i in range(n_chunks):
        start_index = i * chunk_size
        end_index = min((i + 1) * chunk_size, len(df.index))
        chunk = (
            df.iloc[start_index:end_index]
            .astype(str)
            .map(lambda x: truncar_texto(x, max_length=max_length))
        )
        resultados.append(chunk)

    return pd.concat(resultados)


def dump_df(df, n=None):
    n = n or 10
    cdf = df.head(n).astype(str)
    try:
        return (
            "\n\n"
            + cdf.to_markdown()
            + (f"\n\n{len(df.index)-n} more..." if len(df.index) > n else "\n")
        )
    except:
        return (
            "\n\n"
            + str(cdf)
            + (f"\n\n{len(df.index)-n} more..." if len(df.index) > n else "\n")
        )


def reduce_details(
    details: pd.DataFrame | set[str] | list[str] | dict[str, str] | None, max_length=64
):
    if isinstance(details, gpd.GeoDataFrame):
        return plot_map(details, title="Map")
    elif isinstance(details, pd.DataFrame):
        return truncar_tabla(details, max_length=max_length)
    elif isinstance(details, (set, list)):
        return [reduce_details(i, max_length=max_length) for i in details]
    elif isinstance(details, dict):
        return {k: reduce_details(v, max_length=max_length) for k, v in details.items()}
    else:
        return details


def plot_map(geodata, title, ax=None):
    fig, ax = plt.subplots(figsize=(6, 8))
    geodata.plot(ax=ax, color='lightblue', edgecolor='black')
    plt.title(title)
    png_buffer = BytesIO()
    plt.savefig(png_buffer, format="png", bbox_inches="tight")
    png_buffer.seek(0)
    img_base64 = base64.b64encode(png_buffer.read()).decode()

    try:
        return f"\n\n<img src=\"data:image/png;base64,{img_base64}\" alt=\"Mapa\" width=\"600\"/>\n\n"
    finally:
        plt.close(fig)


class Reportable:
    def __init__(self):
        self.report = []
        self.is_prev_loaded = False

    def message(
        self,
        typo: str,
        message: str,
        details: pd.DataFrame | set[str] | list[str] | dict[str, str] | None,
    ):
        self.report.append(
            {
                "type": typo,
                "message": message,
                "details": reduce_details(details),
            }
        )

    def info(self, message, details: pd.DataFrame | list[str] | dict[str, str] = None):
        self.message("info", message, details)

    def warning(
        self, message, details: pd.DataFrame | list[str] | dict[str, str] = None
    ):
        self.message("warning", message, details)

    def error(self, message, details: pd.DataFrame | list[str] | dict[str, str] = None):
        self.message("error", message, details)

    def reset(self):
        try:
            return self.report
        finally:
            self.report = []

    def get_report(self):
        return self.report

    def is_set(self):
        return self.is_prev_loaded

    def set_report(self, report):
        self.report = report
        self.is_prev_loaded = True
