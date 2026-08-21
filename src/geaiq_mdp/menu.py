from collections import defaultdict
import os
import html
from pathlib import Path
import requests
import uuid
import logging

from geaiq_mdp.cache import cache
from geaiq_mdp.processors import get_processor
from geaiq_mdp.data import load_data
from geaiq_mdp.enums import SourceStatus
from geaiq_mdp.io_sources import iter_sources
from geaiq_mdp.parsers import parse_menu, parse_metadata
from geaiq_mdp.persistent_anchor_yaml import PersistentAnchorYAML

# La base de la API que termina EN EL REPORTE es la que va a usar un BROWSER: el
# `fetch` del formulario y el `<a href>` de cada instancia. Tiene que ser RELATIVA.
#
# `GEAIQ_API_URL` NO sirve para esto: en `airflow-scheduler` —que es justamente el
# container donde el DAG genera los reportes— vale `http://geaiq_api:8000`, la URL
# interna de Docker. Inyectarla deja una página pública apuntando a un host que el
# browser del curador no puede resolver. El default público sólo se veía corriendo
# giqmd a mano, sin esa env var: por eso la prueba manual del 20-ago dio 201 y el
# camino del DAG habría fallado igual.
#
# Relativa acierta siempre y no la puede envenenar ninguna env var: el reporte se
# sirve DESDE el dominio de la API (`static.py`), que es la misma premisa que hace
# funcionar al token de `localStorage` — si no fueran el mismo origen, no habría
# token que leer y el formulario no podría escribir de todos modos.
geoecon_api_url = os.environ.get("GEAIQ_PUBLIC_API_URL", "/api/v1").rstrip("/")
# Sin el `rstrip` de acá el href salía con `//` (`/ui/instances//<uuid>`), porque
# el f-string de abajo ya pone su propia barra.
instances_url = f"{geoecon_api_url}/ui/instances"


def generate_menu_form(
    name=None,
    instance_uuid=None,
    menu_uuid=None,
    slug=None,
    country=None,
    scale=None,
    period=None,
    topic=None,
    indicator_1=None,
    indicator_2=None,
    indicator_3=None,
    indicator_4=None,
    indicator_5=None,
    description=None,
    resume=None,
):
    # Función auxiliar para manejar valores nulos
    def input_value(value):
        return f'value="{value}"' if value else ""

    def textarea_value(value):
        return value if value else ""

    form_uuid = uuid.uuid4()

    return f"""
<div class="menu-form">
<h3>
    <a href="javascript:void(0);" onclick="toggleForm('ins{form_uuid}')">[+]</a>
    <a href="{instances_url}/{instance_uuid}">{name}</a>
</h3>
<div class="actions"></div>
<form id="ins{form_uuid}" instance_uuid="{instance_uuid}" onsubmit="postToGeoEcon('ins{form_uuid}'); return false;">
    <div class="form_input">
    <div><label>UUID:</label> <input type="text" class="muuid" {input_value(menu_uuid)}></div>
    <div><label>Slug:</label> <input type="text" class="slug" required {input_value(slug)}></div>
    <div><label>Country:</label> <input type="text" class="country" required {input_value(country)}></div>
    <div><label>Scale:</label> <input type="text" class="scale" required {input_value(scale)}></div>
    <div><label>Period:</label> <input type="text" class="period" required {input_value(period)}></div>
    <div><label>Topic:</label> <input type="text" class="topic" required {input_value(topic)}></div>
    <div><label>Indicator 1:</label> <input type="text" class="indicator_1" {input_value(indicator_1)}></div>
    <div><label>Indicator 2:</label> <input type="text" class="indicator_2" {input_value(indicator_2)}></div>
    <div><label>Indicator 3:</label> <input type="text" class="indicator_3" {input_value(indicator_3)}></div>
    <div><label>Indicator 4:</label> <input type="text" class="indicator_4" {input_value(indicator_4)}></div>
    <div><label>Indicator 5:</label> <input type="text" class="indicator_5" {input_value(indicator_5)}></div>
    <div><label>Description:</label> <textarea class="description" required>{textarea_value(description or "No description provided.")}</textarea></div>
    <div><label>Resume:</label> <textarea class="resume" required>{textarea_value(resume or "No resume provided.")}</textarea></div>
    </div>
    <div class="btn"><button type="submit">Agregar/Actualizar Menú</button></div>
</form>
</div>
"""


OPENIA_APIKEY = os.environ.get("OPENIA_APIKEY")

IA_TEXT = """
Haceme un texto que resuma en 100 palabras el siguiente contenido, en tres parrafos, introducción, descripción 
y utilidad específica del indicador y con que otros indicadores se pueden combinar.
"""


def generate_summary(description):
    """Generates a summary using a large language model."""
    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta2/models/text-bison-001:generateText",  # Replace with actual Gemini endpoint if different
            json={
                "prompt": f"{IA_TEXT}\n\n{description}",
                "temperature": 0.7,  # Adjust as needed
                "max_tokens": 100,  # Adjust as needed
            },
            headers={
                "Content-Type": "application/json",  # Essential for JSON payloads
            },
        )

        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        summary = response.json()["choices"][0]["text"]
        return summary
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return None


class Breadcrumb(object):
    def __init__(self, option_list):
        self.options = {
            o.name: o for o in option_list
        }
        self.groups = {
            sg.name: sg for o in option_list if o.select for sg in o.select.shape_groups
        }
        self.dimensions = {
            f"{d.name}[{d.group}]": d
            for o in option_list
            if o.select
            for d in o.select.dimensions
        }
        
    def opt_path(self):
        return ' / '.join(self.options)

    def group_names(self):
        return ', '.join(self.groups)

    def dim_names(self):
        return ', '.join(self.dimensions)
    
    def shared_dimensions(self, s_dimensions):
        return set(s_dimensions).intersection(self.dimensions.values())
    
    def debug(self):
        return any(o.debug for o in self.options.values())
    
    def __str__(self):
        return f"### {self.opt_path()}\n" \
            f"  - *Shape groups*: {self.group_names()}\n" \
            f"  - *Dimensions*: {self.dim_names()}\n"


class Menu(object):
    def __init__(self, geoecon_api, full=False):
        self.geoecon_api = geoecon_api
        self.full = full
        self.menu_rows = []

    def load(self, root=None, metadata=[]):
        root = root or Path("./")
        menu_path = root / "menu" / "menu.yml"
        if not menu_path.exists():
            logging.error("Menu directory not found: %s", menu_path)
        else:
            reader = PersistentAnchorYAML(typ="safe", pure=True)
            load_data(root=root, reader=reader)
            self.menu = parse_menu(menu_path, reader)
            # `iter_sources` YA arma el aviso de cada fuente descartada por status,
            # pero acá se tiraba a una lista local que nadie leía: el reporte salía
            # con cero formularios y EXIT=0, indistinguible de "no hay candidatos".
            # Se guarda para que `process()` lo escriba en el ARTEFACTO — un cero
            # tiene que decir POR QUÉ es cero.
            self.load_report = []
            self.sources = list(
                iter_sources(
                    metadata,
                    report=self.load_report,
                    expected_status=SourceStatus.DEPLOYED,
                    reader=reader,
                )
            )

    def breadcrumbs(self):
        return (
            Breadcrumb(breadcrumb) for opening in self.menu for breadcrumb in opening.optioniter()
        )

    def iteropennings(self):
        for op in self.menu:
            yield op
            for sop in op.optioniter():
                yield sop

    @cache("source", lambda self, s: s.slug)
    def get_source(self, source):
        return self.geoecon_api.get_source(source)

    def get_source_map(self, sources):
        return {s.slug: self.get_source(s) for s in sources}

    @cache("instances", lambda self, slug: slug)
    def get_instances(self, slug):
        return (
            [
                self.geoecon_api.get_instance(inst_ref["uuid"])
                for inst_ref in self.geoecon_api.get_instances(
                    source_uuid=self.source_map[slug]["uuid"]
                )
            ]
            if self.source_map[slug]
            else []
        )

    def get_instance_map(self, sources):
        return {s.slug: self.get_instances(s.slug) for s in sources}

    def retrieve(self):
        self.source_map = self.get_source_map(self.sources)
        self.instances_map = self.get_instance_map(self.sources)
        self.build_ref_instance_map()

    def build_ref_instance_map(self):
        self.uuid_instance_map = {
            instance["uuid"]: instance
            for instances in self.instances_map.values()
            for instance in instances
        }

        self.ref_instance_map = defaultdict(list)
        for uuid, ins in self.uuid_instance_map.items():
            for k in ins["indicator"]["name"].split("/"):
                self.ref_instance_map[k].append(uuid)

    def get_instances_by_dims(self, *dimensions):
        return set.intersection(*(set(self.ref_instance_map[d]) for d in dimensions))

    def get_dimension_names(self, *dimensions):
        return [f"{d.name}[{d.group}]" for d in dimensions]

    def form(self, breadcrumb, instance):
        country, topic, *options = breadcrumb.options
        scale = instance["scale"]
        period = instance["data_period"]
        description = "\n\n".join(o.description for o in breadcrumb.options.values()) + (
            instance["description"] or ""
        )
        return generate_menu_form(
            **{
                "name": html.escape(instance["name"]),
                "instance_uuid": html.escape(instance["uuid"]),
                "description": html.escape(description),
                "resume": html.escape(""),
                "slug": html.escape(instance["code"]),
                "country": html.escape(country),
                "scale": html.escape(scale["name"]),
                "period": html.escape(period["name"]),
                "topic": html.escape(topic),
                "indicator_1": html.escape(options[0]),
                "indicator_2": (
                    html.escape(options[1]) if len(options) > 1 else None
                ),
                "indicator_3": (
                    html.escape(options[2]) if len(options) > 2 else None
                ),
                "indicator_4": (
                    html.escape(options[3]) if len(options) > 3 else None
                ),
                "indicator_5": (
                    html.escape(options[4]) if len(options) > 4 else None
                ),
            }
        )

    def skipped_sources(self):
        """Fuentes que `load()` descartó, con el motivo. Ver `load()`."""
        for entry in getattr(self, "load_report", []):
            for source in entry.get("sources", []):
                for slug, messages in source.items():
                    for message in messages:
                        yield entry.get("file", "?"), slug, message.get("message", "")

    def process(self, output):

        output.write("# Menu\n")

        # Antes que nada, lo que NO se va a poder curar y por qué. Si esto va al
        # final —o sólo al log— el curador lee un reporte vacío como si el
        # catálogo ya estuviera al día.
        skipped = list(self.skipped_sources())
        if skipped:
            output.write(
                "\n> ⚠️ **Hay fuentes que este reporte NO pudo mirar.** No es que no "
                "tengan candidatos: quedaron afuera antes de evaluarse. `menu` sólo "
                "toma fuentes con `status: deployed`, y avanzar ese status es MANUAL "
                "en el YAML — giqmd nunca lo escribe de vuelta.\n\n"
            )
            output.write("| Archivo | Fuente | Motivo |\n|---|---|---|\n")
            for file, slug, message in skipped:
                output.write(f"| `{file}` | `{slug}` | {message} |\n")
            output.write("\n")

        output_lesser_candidates = ""

        for s in self.sources:
            processor = get_processor(s)
            s._explode_dimensions = processor.dimension_exploder(s)

        all_breadcrumbs = self.breadcrumbs()
        for breadcrumb in all_breadcrumbs:
            if self.full:
                output.write(breadcrumb)
                
            for s in self.sources:
                if s.shape.group.name in breadcrumb.groups:
                    options = []
                    option_candidate = False
                    for c in s.columns:
                        i_dimensions = breadcrumb.shared_dimensions(s._explode_dimensions(c))
                        if i_dimensions and all(i_dimensions):
                            options.append((c, i_dimensions))
                            if set(i_dimensions) == set(c.dimensions):
                                option_candidate = (c, i_dimensions)
                        else:
                            pass

                        l_options = [len(o[1]) for o in options]
                        if len(options) > 1 and min(l_options) < max(l_options):
                            options = [options[l_options.index(max(l_options))]]
                        elif len(options) > 1:
                            continue

                    if not options:
                        continue

                    similars = all(
                        o.period != options[0][0].period and d == options[0][1]
                        for o, d in options[1:]
                    )

                    if not option_candidate and len(options) > 1 and not similars:
                        output_lesser_candidates += str(breadcrumb)

                        for i, (c, ds) in enumerate(options):
                            output_lesser_candidates += f"    - {c.name}\n"
                            for d in c.dimensions:
                                if d in set(d for e in ds for d in e):
                                    output_lesser_candidates += (
                                        f"        - **{d.name}[{d.group}]**\n"
                                    )
                                else:
                                    output_lesser_candidates += (
                                        f"        - {d.name}[{d.group}]\n"
                                    )

                    if option_candidate or len(options) == 1 or similars:
                        if not self.full:
                            output.write(str(breadcrumb))

                        _, i_dimensions = options[0]

                        output.write(f"      * Source: {s.slug}\n")
                        output.write(
                            f"      * Columns: {','.join(c.name for c, _ in options)}\n"
                        )
                        output.write(
                            f"      * Shared dimensions: {', '.join(self.get_dimension_names(*i_dimensions))}\n"
                        )
                        output.write(f"      * Instances:\n")

                        for uuid in self.get_instances_by_dims(*breadcrumb.dimensions.keys()):
                            inst = self.uuid_instance_map[uuid]
                            output.write(f"\n\n{self.form(breadcrumb, inst)}\n\n")

                    if output_lesser_candidates:
                        output.write(output_lesser_candidates)
                elif False:
                    logging.debug(
                        "Ignoring %s because %s not in groups %s",
                        [b.name for b in breadcrumb],
                        s_group.name,
                        bc_group_names,
                    )
                else:
                    pass

    def iter(self):
        if self.menu is None:
            return

        for op in self.menu:
            yield op
            for sop in op.iter():
                yield sop

    def download_tags(self):
        tags = []
        page = 1
        while (data := self.geoecon_api.get("ui/tst", params={"page": page})) and data[
            "items"
        ]:
            tags += data["items"]
            page = data["page"] + 1
        return tags

    def upload_tags(self, output, no_upload=False):
        if not no_upload:
            old_tags = {
                f"{v['tag']['name']}[{v['tag_scope']['code']}]": v["tag"]["uuid"]
                for v in self.download_tags()
            }

        tags = {}
        for op in self.iter():
            tags[f"{op.name}[{op.scope}]"] = op

        output.write("# Tags\n")
        for k, t in tags.items():
            output.write(f"### Tag: '{t.name}' [{t.scope}]\n")
            output.write(f"\n{t.description}\n")

            if no_upload:
                continue
            else:
                t.upload_tag(self.geoecon_api, old_tags.get(k))

        output.write("# Done\n")
