import logging
from pathlib import Path
from geoecon_metadata.data import load_data
from geoecon_metadata.io_sources import iter_sources
from geoecon_metadata.processors import get_processor
from geoecon_metadata.enums import Environments, SourceStatus
from geoecon_metadata.persistent_anchor_yaml import PersistentAnchorYAML


def deployer(file_iter, target: Environments, only_new=True, root=None):
    report = []
    reader = PersistentAnchorYAML(typ="safe", pure=True)

    data = load_data(reader=reader, root=root)

    reader.push_anchors()

    for src in iter_sources(
        file_iter, report, expected_status=SourceStatus.VALID, reader=reader
    ):
        logging.info("Deploying %s", src.slug)

        if only_new and target.get_source(src) is not None:
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
