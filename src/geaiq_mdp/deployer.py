import logging
from pathlib import Path
from geaiq_mdp.data import load_data
from geaiq_mdp.geoecon_api import GEOECON_API_MAP
from geaiq_mdp.io_sources import iter_sources
from geaiq_mdp.processors import get_processor
from geaiq_mdp.enums import Environments, SourceStatus
from geaiq_mdp.persistent_anchor_yaml import PersistentAnchorYAML


def deployer(file_iter, target: Environments, only_new=True, root=None):
    report = []
    reader = PersistentAnchorYAML(typ="safe", pure=True)

    data = load_data(reader=reader, root=root)

    reader.push_anchors()

    geoecon_api = GEOECON_API_MAP[target]() if only_new else None

    for src in iter_sources(
        file_iter, report, expected_status=SourceStatus.VALID, reader=reader
    ):
        logging.info("Deploying %s", src.slug)

        if only_new and geoecon_api.get_source(src) is not None:
            logging.info("Ignoring existing source %s", src.slug)
            continue

        report[-1]["sources"].append(
            {
                src.slug: get_processor(src).deploy(
                    src, environment=target, context=data
                )
            }
        )
        type_list = [
            m["type"] for s in report[-1]["sources"] for k, ms in s.items() for m in ms
        ]
        if with_errors := "error" in type_list:
            report[-1]["report"].append({"type": "error", "message": "Error on deploy."})
        elif not "report" in report[-1]:
            report[-1]["report"].append({
                "type": "info",
                "message": "No errors detected on deploy.",
            })
        logging.info(
            "Deployed %s: %s", src.slug, "with errors" if with_errors else "Ok"
        )

    return report
