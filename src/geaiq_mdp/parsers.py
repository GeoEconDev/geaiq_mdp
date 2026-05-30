from functools import cache
from pathlib import Path
from typing import List
from pydantic import TypeAdapter
from geaiq_mdp.persistent_anchor_yaml import PersistentAnchorYAML
import logging
from .models import (
    IncludeOptions,
    MenuOption,
    Source,
    register
)


def parse_yaml_raw(model_type, yaml_file, reader=None):
    reader = reader or PersistentAnchorYAML(typ="safe", pure=True)  # YAML 1.2 support
    objects = register(reader).load(yaml_file)
    ta = TypeAdapter(model_type)  # type: ignore
    return ta.validate_python(objects) if objects else None


def parse_metadata(yaml_file, reader=None):
    reader = reader or PersistentAnchorYAML(typ="safe", pure=True)
    return parse_yaml_raw(List[Source], yaml_file, reader=reader)


def parse_menu(filename, reader=None):
    reader = reader or PersistentAnchorYAML(typ="safe", pure=True)
    ifile = Path(filename)
    logging.info("Loading %s", ifile)
    with ifile.open(mode="r", encoding="utf-8") as yaml_file:
        return parse_yaml_raw(IncludeOptions | List[MenuOption], yaml_file, reader=reader)

def dump_metadata(src):
    reader = reader or PersistentAnchorYAML(typ="safe", pure=True)
    ifile = Path(filename)
    logging.info("Loading %s", ifile)
    with ifile.open(mode="r", encoding="utf-8") as yaml_file:
        return parse_yaml_raw(IncludeOptions | List[MenuOption], yaml_file, reader=reader)