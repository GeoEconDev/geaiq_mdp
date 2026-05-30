from typing import List, Any
from geaiq_mdp.models import (
    ObservableGroup,
    ObservableScale,
    Period,
    Attribute,
    IndicatorInstanceGenerators,
    Indicator,
    ObservableClass,
    register,
)
from .parsers import parse_yaml_raw
from .persistent_anchor_yaml import PersistentAnchorYAML


def read_data(yaml_file, reader=None):
    reader = reader or PersistentAnchorYAML(typ="safe", pure=True)
    return parse_yaml_raw(
        List[ObservableScale | ObservableGroup | Period | Attribute | IndicatorInstanceGenerators | Indicator | ObservableClass | List[Any]],
        yaml_file,
        reader=reader,
    )


def read_obs_groups(yaml_file, reader=None):
    reader = reader or PersistentAnchorYAML(typ="safe", pure=True)
    return parse_yaml_raw(List[ObservableGroup], yaml_file, reader=reader)


def read_obs_scales(yaml_file, reader=None):
    reader = reader or PersistentAnchorYAML(typ="safe", pure=True)
    return parse_yaml_raw(List[ObservableScale], yaml_file, reader=reader)


def dump(content, stream):
    writer = PersistentAnchorYAML(typ="safe", pure=True)  # YAML 1.2 support
    register(writer).dump(content, stream)
