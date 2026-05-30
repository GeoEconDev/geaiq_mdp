from datetime import date
from typing import ClassVar, Optional
from uuid import UUID
from .geoecon_api import GeoEconAPIModel
from .wh import Attribute


class IndicatorInstanceGenerators(GeoEconAPIModel):
    yaml_tag: ClassVar = "!IndicatorInstanceGenerators"
    geoecon_api_endpoint: ClassVar = "ui/indicator_generators"

    uuid: Optional[UUID] = None
    name: str
    code: str
    description: str
    call_reference: str
    base_payload: dict
    input_parameters_schema: dict

    def geoecon_api_key(self, geoecon_api=None):
        return {"name": self.name}

    def geoecon_api_data(self):
        return {
            **self.geoecon_api_key(),
            "code": self.code,
            "description": self.description,
            "call_reference": self.call_reference,
            "base_payload": self.base_payload,
            "input_parameters_schema": self.input_parameters_schema
        }

    @classmethod
    def from_yaml(self, constructor, node):
        return self(**constructor.construct_mapping(node, deep=True))


class Indicator(GeoEconAPIModel):
    yaml_tag: ClassVar = "!Indicator"
    geoecon_api_endpoint: ClassVar = "ui/indicators"

    uuid: Optional[UUID] = None
    name: str
    code: str
    order: int
    cluster_algorithm: str
    attribute: Attribute
    instance_generator: IndicatorInstanceGenerators

    def geoecon_api_key(self, geoecon_api=None):
        return {"name": self.name}

    def geoecon_api_data(self):
        return {
            **self.geoecon_api_key(),
            "code": self.code,
            "order": self.order,
            "attribute": self.attribute.geoecon_api_key(),
            "cluster_algorithm": self.cluster_algorithm,
            "instance_generator": self.instance_generator.geoecon_api_key(),
            "topics": [],
            "instances": []
        }

    @classmethod
    def from_yaml(self, constructor, node):
        return self(**constructor.construct_mapping(node, deep=True))
