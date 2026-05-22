from pathlib import Path
import pandas as pd
from pydantic import BaseModel
from typing import ClassVar
from ruamel.yaml.nodes import ScalarNode
from ruamel.yaml.constructor import ConstructorError

from geoecon_metadata.persistent_anchor_yaml import PersistentAnchorYAML


class ColumnRef(BaseModel):
    yaml_tag: ClassVar = f"!ColumnRef"
    ref: str

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_scalar(cls.yaml_tag, f"{node.ref}")

    @classmethod
    def from_yaml(cls, constructor, node):
        if isinstance(node, ScalarNode):
            return cls(ref=node.value)
        else:
            raise ConstructorError(
                None,
                None,
                f"expected a scalar node, but found {node.id!s}",
                node.start_mark,
            )

    def __hash__(self):
        return hash(self.ref)


class IncludeOptions(BaseModel):
    yaml_tag: ClassVar = f"!Include"

    @classmethod
    def from_yaml(cls, constructor, node):
        from geoecon_metadata.parsers import parse_menu

        if isinstance(node, ScalarNode):
            files = node.value.split(" ")
            reader = PersistentAnchorYAML(
                typ="safe",
                pure=True,
                anchors=constructor.composer.anchors,
                anchor_stack=constructor.composer.anchor_stack,
            )
            options = [parse_menu(file, reader) for file in files]
            for os, ts in zip(options[-1:0:-1], options[-2::-1]):
                for t in ts:
                    t.options = os
            return options[0]
        else:
            raise ConstructorError(
                None,
                None,
                f"expected a scalar node, but found {node.id!s}",
                node.start_mark,
            )


def isref(node):
    return isinstance(node, ColumnRef)


def unref(node, df: pd.DataFrame):
    return df[node.ref] if isref(node) else node


def resolve_uuids(node, knows_ref):
    if isinstance(node, pd.DataFrame):
        return node.apply(lambda x: str(knows_ref[x.lower()].uuid))
    else:
        return str(knows_ref[node.name.lower()].uuid)


def resolve_unrefs_uuid(node, in_data, knows_ref):
    return resolve_uuids(unref(node, in_data), knows_ref)
