from typing import ClassVar
from pydantic import BaseModel, field_validator
from .utils import ColumnRef, isref


class Dimension(BaseModel):
    yaml_tag: ClassVar = f"!Dimension"

    name: ColumnRef | str
    group: str
    dependant: ColumnRef | None = None

    def __key(self):
        return (self.name, self.group)

    def __hash__(self):
        return hash(self.__key())

    @field_validator("name", mode="before")
    def validate_name(cls, v):
        if isinstance(v, ColumnRef):
            return v
        return str(v)

    def column_refs(self, independent=True):
        if isinstance(self.name, ColumnRef) and (
            not independent or self.dependant is None
        ):
            yield self.name

    def get_names(self, data):
        if isref(self.name):
            return data[self.name.ref].drop_duplicates().astype(str).apply(lambda n: f"{n}[{self.group}]")
        else:
            return [f"{self.name}[{self.group}]"]

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict({"name": node.name, "group": node.group})
