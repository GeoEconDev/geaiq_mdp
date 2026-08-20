import pandas as pd
from geaiq_mdp.report import Reportable, format_message_markdown


def test_report_info_instance_dataframe():
    report = Reportable()
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    instance = {"c": 5, "d": 6}
    report.info("test", [instance, df])
    format_message_markdown({"report": report.report})


def test_menu_scripts_html_embeds_the_form_js():
    """El reporte del menú tiene que traer su JS adentro.

    Cuando el <script> apuntaba a un estático que no existe (el bucket de GCP
    quedó muerto tras la migración), `postToGeoEcon` quedaba indefinida: el
    reporte se veía perfecto y el botón no escribía una fila en `ui.t_menu`.
    """
    from geaiq_mdp.report import menu_scripts_html

    html = menu_scripts_html("https://api.geaiq.com/api/v1")

    assert "function postToGeoEcon" in html, "el JS no viajó en el paquete"
    assert '"https://api.geaiq.com/api/v1"' in html
    # La credencial NUNCA va en el documento: los reportes se sirven públicos.
    assert "gq_tok" in html and "localStorage" in html


def test_head_html_places_the_scripts_inside_head():
    from geaiq_mdp.report import head_html, menu_scripts_html

    head = head_html("t", extra_head=menu_scripts_html("https://x/api/v1"))

    assert head.index("function postToGeoEcon") < head.index("</head>")


def test_head_html_without_extra_head_is_unchanged():
    """Los reportes que no son de menú no cargan nada extra."""
    from geaiq_mdp.report import head_html

    assert "<script>" not in head_html("t").split("</head>")[0].split("</style>")[1]
