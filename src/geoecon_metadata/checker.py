import logging
from .data import load_data
from .enums import Environments, SourceStatus
from .io_sources import iter_sources
from .persistent_anchor_yaml import PersistentAnchorYAML
from .processors import get_processor


def checker(file_iter, target: Environments, only_new=True, reader=None, root=None):
    report = []
    reader = reader or PersistentAnchorYAML(typ="safe", pure=True)
    
    load_data(reader=reader, root=root)
    
    reader.push_anchors()

    for src in iter_sources(file_iter, report, expected_status=SourceStatus.READY, reader=reader):
        logging.info("Checking %s", src.slug)

        if only_new and target.get_source(src) is not None:
            logging.info("Ignoring existing source %s", src.slug)
            continue

        report[-1]["sources"].append(
            {src.slug: get_processor(src).check(src, target)}
        )
        type_list = [
            m["type"] for s in report[-1]["sources"] for k, ms in s.items() for m in ms
        ]
        if with_errors := "error" in type_list:
            report[-1]["report"] = {"type": "error", "message": "Error on sources."}
        elif not "report" in report[-1]:
            report[-1]["report"] = {
                "type": "info",
                "message": "No errors detected on sources.",
            }
        logging.info("Checked %s: %s", src.slug, "with errors" if with_errors else "Ok")

    return report
