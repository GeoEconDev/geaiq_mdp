from datetime import date
from typing import ClassVar, Optional
from uuid import UUID

from pydantic import PrivateAttr, model_validator, root_validator

from geaiq_mdp.enums import ObservableScaleTypeEnum
from .geoecon_api import GeoEconAPIModel


class Class_(GeoEconAPIModel):
    yaml_tag: ClassVar = "!Class"
    geoecon_api_endpoint: ClassVar = "wh/classes"

    uuid: Optional[UUID] = None
    name: str
    typo: str
    description: str

    def geoecon_api_key(self, geoecon_api=None):
        return {"name": self.name, "type": self.typo}

    def geoecon_api_data(self):
        return {**self.geoecon_api_key(), "description": self.description}

    @classmethod
    def from_yaml(self, constructor, node):
        return self(**constructor.construct_mapping(node, deep=True))
    
    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {
                "uuid": node.uuid,
                "name": node.name,
                "typo": node.typo,
                "description": node.description,
            }
        )

class Period(GeoEconAPIModel):
    yaml_tag: ClassVar = f"!Period"
    geoecon_api_endpoint: ClassVar = "wh/periods"

    uuid: Optional[UUID] = None
    name: str
    description: str
    start_date: date = date.today()
    end_date: date = date.today()

    def __hash__(self):
        return hash(self.name)

    @classmethod
    def from_yaml(self, constructor, node):
        return self(**constructor.construct_mapping(node, deep=True))

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {
                "uuid": node.uuid,
                "name": node.name,
                "description": node.description,
                "start_date": node.start_date,
                "end_date": node.end_date,
            }
        )

    def geoecon_api_key(self, geoecon_api=None):
        return {"name": self.name}

    def geoecon_api_data(self):
        return {
            **self.geoecon_api_key(),
            "description": self.description,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }


class ObservableScale(GeoEconAPIModel):
    yaml_tag: ClassVar = f"!ObservableScale"
    geoecon_api_endpoint: ClassVar = "wh/observables/scales"

    uuid: Optional[UUID] = None
    name: str
    description: str
    group: Optional["ObservableGroup"] = None
    abstract_scale: Optional["ObservableScale"] = None
    concrete_scales: list["ObservableScale"] = []
    typo: ObservableScaleTypeEnum
    aliases: list[str] = []

    def set_group(self, group):
        if self.abstract_scale:
            self.group = group
        return self

    def model_dump(self, **kwargs):
        return super().model_dump(exclude={"concrete_scales"}, **kwargs)

    @model_validator(mode="after")
    def complete_concrete_scales(cls, values):
        if abstract_scale := values.abstract_scale:
            # Agrega la escala actual a la lista de concrete_scales de la abstracta
            if values not in abstract_scale.concrete_scales:
                abstract_scale.concrete_scales.append(values)
        return values

    @classmethod
    def __map_slug__(self, map):
        return f"{map['name']}/{map['group']['name'] if map['group'] else ''}/{map['abstract_scale']['name'] if map['abstract_scale'] else ''}"

    def __slug__(self):
        return f"{self.name}/{self.group.name if self.group else ''}/{self.abstract_scale.name if self.abstract_scale else ''}"

    def __hash__(self):
        return hash(self.__slug__)

    @classmethod
    def from_yaml(cls, constructor, node):
        return cls(**constructor.construct_mapping(node, deep=True))

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {
                "uuid": node.uuid,
                "name": node.name,
                "description": node.description,
                "group": node.group,
                "abstract_scale": node.abstract_scale,
                "concrete_scales": node.concrete_scales,
                "typo": node.typo.value,
                "aliases": node.aliases,
            }
        )
        
    @classmethod
    def expand(cls, scales: "ObservableScale"):
        return scales + [
            con_scale
            for abs_scale in scales
            for con_scale in abs_scale.concrete_scales
            if con_scale is not None
        ]

    def geoecon_api_key(self, geoecon_api=None):
        if self.group and self.group.uuid is None:
            group = self.group.get(geoecon_api)
            if group:
                self.group.uuid = group.uuid
            else:
                raise ValueError("Not uuid for group")
        if self.abstract_scale and self.abstract_scale.uuid is None:
            abssca = self.abstract_scale.get(geoecon_api)
            if abssca:
                self.abstract_scale.uuid = abssca.uuid
            else:
                raise ValueError("Not uuid for abstract scale")

        return {
            "name": self.name,
            "group_uuid": self.group.uuid if self.group else None,
            "abstract_scale_uuid": (
                self.abstract_scale.uuid if self.abstract_scale else None
            ),
        }

    def geoecon_api_data(self):
        return {
            "name": self.name,
            "description": self.description,
            "type": self.typo.value,
            "group": self.group.geoecon_api_key() if self.group else None,
            "abstract_scale": (
                self.abstract_scale.geoecon_api_key() if self.abstract_scale else None
            ),
        }


class ObservableGroup(GeoEconAPIModel):
    yaml_tag: ClassVar = f"!ObservableGroup"
    geoecon_api_endpoint: ClassVar = "wh/observables/groups"

    uuid: Optional[UUID] = None
    name: str
    typo: str
    description: str
    scales: list[ObservableScale]

    def __hash__(self):
        return hash(self.name)

    def model_dump(self, **kwargs):
        return super().model_dump(exclude={"scales"}, **kwargs)

    @classmethod
    def from_yaml(self, constructor, node):
        obsgrp_map = constructor.construct_mapping(node, deep=True)
        obsgrp = self(**obsgrp_map)
        for s in obsgrp.scales:
            s.group = obsgrp
        return obsgrp
    
    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {
                "uuid": node.uuid,
                "name": node.name,
                "typo": node.typo,
                "description": node.description,
                "scales": node.scales,
            }
        )
        
    def geoecon_api_key(self, geoecon_api=None):
        return {"name": self.name, "type": self.typo}

    def geoecon_api_data(self):
        return {
            **self.geoecon_api_key(),
            "description": self.description,
        }

    def subitems(self):
        for scale in self.scales:
            if scale.group is None:
                scale.group = self
            yield scale


class Attribute(GeoEconAPIModel):
    yaml_tag: ClassVar = f"!Attribute"
    geoecon_api_endpoint: ClassVar = "wh/attributes"

    uuid: Optional[UUID] = None
    name: str
    description: str
    unit: str
    parent_uuid: Optional[UUID] = None

    def __hash__(self):
        return hash(self.name)

    @classmethod
    def from_yaml(self, constructor, node):
        return self(**constructor.construct_mapping(node, deep=True))
    
    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {
                "uuid": node.uuid,
                "name": node.name,
                "description": node.description,
                "unit": node.unit,
                "parent_uuid": node.parent_uuid,
            }
        )
        
    def geoecon_api_key(self, geoecon_api=None):
        return {"name": self.name, "unit": self.unit}

    def geoecon_api_data(self):
        return {
            **self.geoecon_api_key(),
            "description": self.description,
        }


class ObservableClass(GeoEconAPIModel):
    yaml_tag: ClassVar = "!ObservableClass"
    geoecon_api_endpoint: ClassVar = "wh/observables/classes"

    uuid: Optional[UUID] = None
    name: str
    description: str

    def geoecon_api_key(self, geoecon_api=None):
        return {"name": self.name}

    def geoecon_api_data(self):
        return {**self.geoecon_api_key(), "description": self.description}

    @classmethod
    def from_yaml(self, constructor, node):
        return self(**constructor.construct_mapping(node, deep=True))

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {
                "uuid": node.uuid,
                "name": node.name,
                "description": node.description,
            }
        )
