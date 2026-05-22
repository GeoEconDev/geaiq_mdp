from ruamel.yaml.representer import RepresenterError
from slugify import slugify
from pathlib import Path
from geoecon_metadata.models import Source, Column, Dimension, ColumnRef
from geoecon_metadata.readers import dump

SOURCES_FIELD_MAP = {
    "active": None,
    "source_id": "slug",
    "#columns": None,
    "description": "description",
    "ref": "ref",
    "drive_share_url": "drive_share_url",
    "method": "method",
    "comment": "comment",
    "reliability": "reliability",
    "source_type": "source_type",
    "source": "source",
    "old_source": None,
    "shape_id": "shape_id",
    "shape_group": "shape_group",
    "shape_period": "shape_period",
    "state": None,
    "source_message": "source_message",
}

POINT_SOURCES_FIELD_MAP = {
    "active": None,
    "source_id": "slug",
    "# columnas": None,
    "description": "description",
    "ref": "ref",
    "method": "method",
    "comment": "comment",
    "reliability": "reliability",
    "source_type": "source_type",
    "source": "source",
    "shape_name": "shape_name",
    "shape_id": "shape_id",
    "shape_group": "shape_group",
    "shape_scale": "shape_scale",
    "shape_class": "shape_class",
    "lat_column": "lat_column",
    "long_column": "long_column",
    "period": "period",
    "state": None,
    "source_message": "source_message",
}

COLUMNS_FIELD_MAP = {
    "active": None,
    "country": None,
    "source_id": "__source_id__",
    "column": "name",
    "attribute": "__dimension_0_name__",
    "period": "period",
    "class": "__dimension_1_name__",
    "class_type": "__dimension_1_group__",
    "unit": "unit",
    "reliability": "reliability",
    "navegable": None,
    "Temática": None,
    "slug": None,
    "column_comment": "comment",
}


def worksheet_to_frame(spreadsheet, name, column_map):
    ws = spreadsheet.worksheet(name)
    rows = ws.get_all_values()
    return [
        {column_map[k]: v for k, v in zip(rows[0], row) if column_map.get(k)}
        for row in rows[1:]
    ]


def to_ref(text):
    return ColumnRef(ref=text[1:]) if text.startswith("@") else text

UNIT_MAP = {
    "": ("TODO", []),
    "pob/km2": ("densidad", [{"name": "pob/km2", "group": "densidad"}]),
    "km2": ("área", [{"name": "km2", "group": "area"}]),
    "m2": ("área", [{"name": "m2", "group": "area"}]),
    "ocupados": ("personas", [{"name": "ocupados", "group": "economía"}]),
    "id": ("identificación", []),
    "indice": ("índice", []),
    "Indice": ("índice", []),
    "ranking": ("índice", []),
    "Score": ("índice", []),
    "egresados": ("personas", [{"name": "egresados", "group": "estado educativo"}]),
    "personas_ed_especial / pob": ("tasa", [{"name": "personas_ed_especial / pob", "group": "tasa educativa"}]),
    "personas_EGB / pob": ("tasa", [{"name": "personas_EGB / pob", "group": "tasa educativa"}]),
    "personas_primario / pob": ("tasa", [{"name": "personas_primario / pob", "group": "tasa educativa"}]),
    "personas_secundario / pob": ("tasa", [{"name": "personas_secundario / pob", "group": "tasa educativa"}]),
    "personas_superior_no_un / pob": ("tasa", [{"name": "personas_superior_no_un / pob", "group": "tasa educativa"}]),
    "personas_total_ed / pob": ("tasa", [{"name": "personas_total_ed / pob", "group": "tasa educativa"}]),
    "personas_universitario / pob": ("tasa", [{"name": "personas_universitario / pob", "group": "tasa educativa"}]),
    "pesos (y otras divisas convertidas)": ("moneda", [{"name": "pesos", "group": "moneda"}]),
    "pesos": ("moneda", [{"name": "pesos", "group": "moneda"}]),
    "dolares": ("moneda", [{"name": "dolares", "group": "moneda"}]),
    "dólares FOB": ("moneda", [{"name": "dólares", "group": "moneda"}, {"name": "FOB", "group": "monto de importación/exportación"}]),
    "miles de dólares FOB": ("moneda", [{"name": "miles de dólares", "group": "moneda"}, {"name": "FOB", "group": "monto de exportación"}]),
    "Miles de pesos a precios básicos": ("moneda", [{"name": "miles de pesos", "group": "moneda"}, {"name": "básico", "group": "precios"}]),
    "Miles de dólares a precios básicos": ("moneda", [{"name": "miles de dólares", "group": "moneda"}, {"name": "básico", "group": "precios"}]),
    "Miles de pesos de 2018 a precios básicos": ("moneda", [{"name": "miles de pesos", "group": "moneda"}, {"name": "básico", "group": "precios"}, {"name": "2018", "grupo": "periodo base"}]),
    "Miles de pesos": ("moneda", [{"name": "miles de pesos", "group": "moneda"}]),
    "miles de pesos 2024": ("moneda", [{"name": "miles de pesos", "group": "moneda"}]),
    "miles de pesos 2004": ("moneda", [{"name": "miles de pesos", "group": "moneda"}]),
    "miles de pesos 2022": ("moneda", [{"name": "miles de pesos", "group": "moneda"}]),
    "Miles de dólares": ("moneda", [{"name": "miles de dólares", "group": "moneda"}]),
    "miles de dolares": ("moneda", [{"name": "miles de dólares", "group": "moneda"}]),
    "miles de dólares": ("moneda", [{"name": "miles de dólares", "group": "moneda"}]),
    "miles de dólares 2023": ("moneda", [{"name": "miles de dólares", "group": "moneda"}]),
    "Promedio en pesos": ("moneda", [{"name": "Promedio en pesos", "group": "moneda"}]),
    "Promedio en dólares": ("moneda", [{"name": "Promedio en dólares", "group": "moneda"}]),
    "pesos mensuales promedio": ("moneda", [{"name": "pesos mensuales promedio", "group": "moneda"}]),
    "pesos mensuales medianos": ("moneda", [{"name": "pesos mensuales medianos", "group": "moneda"}]),
    "indice (cada mil habitantes)": ("tasa", [{"name": "Persona", "group": "Demografía humana"}, {"name": "1000 habitantes", "group": "dominio"}]),
    "Ocupados cada mil habitantes": ("índice", [{"name": "Ocupados", "group": "Economía"}, {"name": "1000 habitantes", "group": "dominio"}]),
    "Empresas cada mil habitantes": ("índice", [{"name": "Empresas", "group": "Economía"}, {"name": "1000 habitantes", "group": "dominio"}]),
    "establecimiento": ("establecimientos", []),
    "Votos": ("votos", []),
    "point parts per billion by volume": ("concentración", [{"name": "partes por mil millones por volumen", "group": "concentración"}]),
    "mol mol^(-1)": ("concentración", [{"name": "mol mol^(-1)", "group": "concentración"}]),
    "Kelvin": ("temperatura", [{"name": "Kelvin", "group": "temperatura"}]),
    "personas por cada mil personas": ("densidad", [{"name": "personas por cada mil personas", "group": "densidad"}]),
    "unidades economicas": ("unidades económicas", []),
    "años": ("tiempo", [{"name": "años", "group": "tiempo"}]),
    "diferencia de rankings": ("índice", [{"name": "diferencia", "group": "índice"}]),
    "vivendas": ("viviendas", []),
    "empresas": ("unidades económicas", []),
    "ocupados/empresas": ("índice", [{"name": "ocupados/empresas", "group": "índice"}]),
    "string": ("identificación", []),
    "país": ("identificación", [{"name": "país", "group": "identificación"}]),
    "establecimientos de salud cada diez mil habitantes": ("establecimientos", [{"name": "establecimientos de salud cada diez mil habitantes", "group": "establecimientos"}, {"name": "10000 habitantes", "group": "contexto"}]), # TODO
}

RELIABILITY_MAP = {
    "inferred": "computed",
    "infered": "computed",
    "conventional_aggregation": "aggregated",
    "unknown": "TODO",
    "trusted": "trust",
}

SOURCE_TYPE_MAP = {
    '': 'TODO',
}

def create_dimensions(column_row):
    dimensions = [
        {"name": to_ref(column_row["__dimension_0_name__"]), "group": "attribute"},
        {
            "name": to_ref(column_row["__dimension_1_name__"]),
            "group": column_row["__dimension_1_group__"],
        },
    ]
    del column_row["__dimension_0_name__"]
    del column_row["__dimension_1_name__"]
    del column_row["__dimension_1_group__"]

    if column_row["unit"] in UNIT_MAP:
        new_unit, new_dimensions = UNIT_MAP[column_row["unit"]]
        column_row["unit"] = new_unit
        dimensions.extend(new_dimensions)
    column_row["reliability"] = RELIABILITY_MAP.get(column_row["reliability"], column_row["reliability"] or 'TODO')
    column_row["period"] = to_ref(column_row["period"])
    
    return Column(**{**column_row, "dimensions": [Dimension(**d) for d in dimensions]})


def rotate_target_files(target_yaml):
    targets_yaml = [target_yaml]
    while targets_yaml[-1].exists():
        targets_yaml.append(targets_yaml[-1].with_suffix(targets_yaml[-1].suffix+".old"))
        
    targets_yaml.reverse()
    for src, tar in zip(targets_yaml[1:], targets_yaml[:-1]):
        src.rename(tar)


def md_import(spreadsheet):
    sources_frame = worksheet_to_frame(spreadsheet, "sources", SOURCES_FIELD_MAP)
    point_sources_frame = worksheet_to_frame(
        spreadsheet, "point_sources", POINT_SOURCES_FIELD_MAP
    )
    columns_frame = worksheet_to_frame(spreadsheet, "columns", COLUMNS_FIELD_MAP)

    for source in sources_frame:
        try:
            source_id = source["slug"] or "TODO"
            columns = [
                create_dimensions(row)
                for row in columns_frame
                if row["__source_id__"] == source_id
            ]
            source["columns"] = columns
            source["slug"] = slugify(source["slug"])
            source["methodological_notes"] = source.get("retrieve_method", "TODO") or "TODO"
            source["retrieve_method"] = source.get("retrieve_method", "TODO") or "TODO"
            source["reliability"] = RELIABILITY_MAP.get(source.get("reliability", source.get("reliability", "TODO"))) or "TODO"
            source["source_type"] = SOURCE_TYPE_MAP.get(source.get("source_type"), source.get("source_type", "TODO")) or "TODO"

            if source_id and source["columns"]:
                target_yaml = Path("metadata/import") / (source_id + ".yml")
                rotate_target_files(target_yaml)                    
                with target_yaml.open("w", encoding="utf8") as f:
                    dump([Source(**source)], f)
            else:
                print("--- Fail to create file ")
                print(source)
                print("")
        except RepresenterError as exc:
            print("--- input:", source_id)
            print(exc)
            print("---")
        except Exception as exc:
            print("--- input:", exc.errors()[0]['input'])
            print(exc)
            print("---")