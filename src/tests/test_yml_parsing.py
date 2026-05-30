from typing import List, Literal, Annotated, ClassVar, Any, Type
from pydantic import (
    BaseModel,
    TypeAdapter,
    field_validator,
    Field,
    model_serializer,
    model_validator,
)

from geaiq_mdp.persistent_anchor_yaml import PersistentAnchorYAML

class ObservableScale(BaseModel):
    yaml_tag: ClassVar = f"!ObservableScale"

    name: str
    description: str

    @classmethod
    def from_yaml(cls, constructor, node):
        data = constructor.construct_mapping(node, deep=True)
        return cls(**data)

    
class ObservableGroup(BaseModel):
    yaml_tag: ClassVar = f"!ObservableGroup"

    name: str
    description: str
    
    @classmethod
    def from_yaml(cls, constructor, node):
        data = constructor.construct_mapping(node, deep=True)
        return cls(**data)
    
    
yml_a = """
- !ObservableScale &aOSA
  name: A
  description: B
- !ObservableGroup &aOSB
  name: B
  description: C
"""

yml_b = """
- !ObservableScale &bOSA
  name: A
  description: BB
- !ObservableGroup &bOSB
  name: B
  description: BC
- *aOSA
"""

from ruamel.yaml import YAML


def read_data(yaml_file, reader=None):
    reader = reader or YAML(typ="safe", pure=True)
    reader.register_class(ObservableScale)
    reader.register_class(ObservableGroup)
    objects = reader.load(yaml_file)
    #ta = TypeAdapter(List[ObservableScale | ObservableGroup])  # type: ignore
    #return ta.validate_python(objects)
    return objects


reader = PersistentAnchorYAML(typ="safe", pure=True)
print("...")
print(read_data(yml_a, reader))
print(f"A Anchors: {reader.composer.anchors} {reader.composer.anchor_stack}")
print(read_data(yml_b, reader))
print(f"B Anchors: {reader.composer.anchors} {reader.composer.anchor_stack}")
