from itertools import product
from pydantic import BaseModel, HttpUrl
from typing import TYPE_CHECKING, ClassVar
from typing import List, Iterator, Any, ClassVar, Optional, Union

from slugify import slugify
import pandas as pd

from geoecon_metadata.models.dimension import Dimension
from geoecon_metadata.models.utils import ColumnRef, isref, unref
from geoecon_metadata.enums import (
    ColumnStatus,
    Encodings,
    MeasurementUnit,
    GroupScaleEnum,
    ObservableWithoutObservationActions,
    ReliabilityType,
    ShapeOperationEnum,
    SourcePlatform,
    SourceStatus,
    SourceType,
)

from pydantic import (
    BaseModel,
    field_validator,
    Field,
    model_validator,
)
from typing import Literal


SLUG_RE = r"^[a-z0-9-]+$"

from .wh import ObservableClass, Period, ObservableScale, ObservableGroup


class SourceReports(BaseModel):
    yaml_tag: ClassVar = "!Reports"

    check: HttpUrl | None = None
    deploy: HttpUrl | None = None
    menu: HttpUrl | None = None


class ObservablesValidation(BaseModel):
    yaml_tag: ClassVar = f"!ObservableValidation"

    shape_scale: Optional[Union[List[ObservableScale] | ObservableScale]] = None
    ignore: list[str] | list[list[str]] | dict[ColumnRef, list[str|int|float]] = []

    def scales(self, _: pd.DataFrame) -> Iterator[ObservableScale]:
        if scale := self.shape_scale:
            if isinstance(scale, list):
                return iter(scale)
            else:
                yield scale
        else:
            return iter([])

    @field_validator("shape_scale", mode="before")
    def validate_name(cls, v):
        return v if isinstance(v, list) else [v]

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {"shape_scale": node.shape_scale, "ignore": node.ignore}
        )


class Validation(BaseModel):
    yaml_tag: ClassVar = f"!Validation"

    observables: ObservablesValidation | None = None

    def scales(self, df: pd.DataFrame) -> Iterator[ObservableScale]:
        if obs := self.observables:
            return obs.scales(df)
        else:
            return iter([])

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {"observables": node.observables, "data": node.data}
        )


class Processing(BaseModel):
    yaml_tag: ClassVar = "!Processing"

    continue_from: str | None = None
    update_geometry: bool = True

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {
                "continue_from": node.continue_from,
                "update_geometry": node.update_geometry,
            }
        )


class ShapeDissolve(BaseModel):
    yaml_tag: ClassVar = f"!ShapeDissolve"

    by: str | None = None
    aggfunc: dict[str, str | list] | None = None

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {"by": node.by, "aggfunc": node.aggfunc}
        )
        

class ShapeTransform(BaseModel):
    yaml_tag: ClassVar = f"!ShapeTransform"

    dissolve: ShapeDissolve | bool | None = None

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {"dissolve": node.dissolve}
        )
        
    
class ObservablesTransform(BaseModel):
    yaml_tag: ClassVar = f"!ObservablesTransform"

    ignore: list[str] | list[list[str]] = []
    shape_scale: Optional[Union[List[ObservableScale], ObservableScale]] = None

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {"ignore": node.ignore, "shape_scale": node.shape_scale}
        )


class DataSubstition(BaseModel):
    yaml_tag: ClassVar = f"!DataSubstition"

    target: ColumnRef
    map: dict[str, str]

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {
                "target": node.target,
                "map": node.map,
            }
        )


def is_list_of_lists(obj):
    return isinstance(obj, list) and all(isinstance(i, list) for i in obj)


class DataSelection(BaseModel):
    yaml_tag: ClassVar = f"!DataSelection"

    ignore: list[str] | list[list[str]] | dict[ColumnRef, list[str|int|float]] = []

    @field_validator("ignore", mode="before")
    def validate_ignore(cls, v):
        if is_list_of_lists(v):
            return [i for sv in v for i in sv]
        return v

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {
                "ignore": node.ignore,
            }
        )


class DataTransform(BaseModel):
    yaml_tag: ClassVar = f"!DataTransform"

    shape_scale: Optional[Union[List[ObservableScale], ObservableScale]] = None
    clone: dict[str, str] = {}
    update: dict[str, str] = {}
    substitute: dict[ColumnRef, dict[str, str]] = {}
    compute: dict[ColumnRef, str] = {}

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {
                "shape_scale": node.shape_scale,
                "clone": node.clone,
                "update": node.update,
                "substitute": node.substitute,
                "compute": node.compute,
            }
        )

    def do_compute(self, df):
        return {
            col.ref: df.apply(eval(to_eval), axis=1)
            for col, to_eval in self.compute.items()
        }


class OnTransform(BaseModel):
    yaml_tag: ClassVar = f"!OnTransform"

    observable_without_observation: ObservableWithoutObservationActions = (
        ObservableWithoutObservationActions.ERROR
    )

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {"observable_without_observation": node.observable_without_observation}
        )


class ObservablesSelection(BaseModel):
    yaml_tag: ClassVar = f"!ObservablesSelection"

    shape_scale: Optional[Union[List[ObservableScale], ObservableScale]] = None
    ignore: list[str] | list[list[str]] | dict[ColumnRef, list[str|int|float]] = []
    filtre: dict[ColumnRef, Any] = {}

    def scales(self, _: pd.DataFrame) -> Iterator[ObservableScale]:
        if scale := self.shape_scale:
            if isinstance(scale, list):
                for s in scale:
                    yield s
            else:
                yield scale
        else:
            return iter([])

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {"shape_scale": node.shape_scale, "ignore": node.ignore}
        )


class Selection(BaseModel):
    yaml_tag: ClassVar = f"!Selection"

    observables: ObservablesSelection | None = None
    data: DataSelection | None = None

    def scales(self, df: pd.DataFrame) -> Iterator[ObservableScale]:
        if obs := self.observables:
            for s in obs.scales(df):
                yield s
        else:
            return iter([])

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {"observables": node.observables, "data": node.data}
        )


class Transform(BaseModel):
    yaml_tag: ClassVar = f"!Transform"

    shape: ShapeTransform | None = None
    observables: ObservablesTransform | None = None
    data: DataTransform | None = None
    on: OnTransform | None = None

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {"observables": node.observables, "data": node.data, "on": node.on}
        )


class Column(BaseModel):
    yaml_tag: ClassVar = f"!Column"

    name: str
    period: Union[Period, ColumnRef]
    unit: MeasurementUnit
    reliability: ReliabilityType
    default_value: Any | None = None
    description: str | None = None
    dimensions: List[Dimension] = Field(min_items=1)
    topic: str | None = "notopic"
    disabled: bool = False
    status: ColumnStatus = ColumnStatus.READY
    eval: str | None = None
    do_group: bool = True
    input_encoding: Encodings = None

    def periods(self, df: pd.DataFrame):
        if isref(self.period):
            yield from iter(set(df[self.period.ref]))
        else:
            yield self.period

    def column_refs(self, independent=True):
        for c in [self.period]:
            if isinstance(c, ColumnRef):
                yield c

        for d in self.dimensions:
            for cf in d.column_refs(independent=independent):
                yield cf

    def __hash__(self):
        return hash(self.name)

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {
                "name": node.name,
                "period": node.period,
                "unit": node.unit.value,
                "description": node.description,
                "reliability": node.reliability.value,
                "dimensions": node.dimensions,
                "default_value": node.default_value,
                "topic": node.topic,
                "disabled": node.disabled,
                "status": node.status.value,
            }
        )

    def class_names(self, df: pd.DataFrame):
        ref_columns = [d.name.ref for d in self.sorted_dimensions if isref(d.name)]
        noref_columns = {
            d.group: d.name for d in self.sorted_dimensions if not isref(d)
        }
        cns = df[ref_columns].rename(
            columns={
                d.name.ref: d.group for d in self.sorted_dimensions if isref(d.name)
            }
        )
        for key, value in noref_columns.items():
            cns[key] = value
        cns = cns.drop_duplicates()[[d.group for d in self.sorted_dimensions]].apply(
            lambda r: "/".join(sorted(r))
        )
        return cns

    @property
    def sorted_dimensions(self):
        return sorted(self.dimensions, key=lambda d: d.group)

    def class_name(self, group_data: dict):
        return "/".join(str(unref(d.name, group_data)) for d in self.sorted_dimensions)

    def class_type(self):
        return "/".join(d.group for d in self.sorted_dimensions)

    @property
    def class_description(self):
        return "\n\n".join(
            f"Dimension:{d.name}\nGroup:{d.group}" for d in self.sorted_dimensions
        )

    @property
    def indicator_name(self):
        return "/".join(d.name for d in self.sorted_dimensions)

    @property
    def indicator_code(self):
        return slugify(self.indicator_name)

    @property
    def indicator_description(self):
        return "/".join(d.name for d in self.sorted_dimensions)

    @property
    def instance_name(self):
        return "-".join([self.name, self.period])

    @property
    def instance_code(self):
        return slugify(self.instance_name)

    def get_indicators(self, data):
        for items in product(*tuple(d.get_names(data) for d in self.sorted_dimensions)):
            yield {"name": (name := "/".join(items)), "code": slugify(name)}


class Point(BaseModel):
    yaml_tag: ClassVar = f"!Shape"

    latitude: str | ColumnRef | None = None
    longitude: str | ColumnRef | None = None

    def to_geometry(self, df: pd.DataFrame):
        if isref(self.latitude) and isref(self.longitude):
            return df[[self.latitude.ref, self.longitude.ref]].apply(
                lambda r: f"POINT ({r[self.longitude.ref]} {r[self.latitude.ref]})",
                axis=1,
            )
        elif self.latitude and self.longitude:
            return f"POINT ({self.longitude} {self.latitude})"
        else:
            return None

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {"latitude": node.latitude, "longitude": node.longitude}
        )

    def __hash__(self):
        return hash((self.longitude, self.longitude))


class Shape(BaseModel):
    yaml_tag: ClassVar = f"!Shape"

    id: str | ColumnRef
    name: str | ColumnRef | None = None
    group: ObservableGroup
    description: str | ColumnRef | None = None
    parent_id: str | ColumnRef | None = None
    period: Union["Period", ColumnRef]
    geometry: str | ColumnRef | Point | None = None
    obs_class: ObservableClass | None = None
    scale: Optional[Union["ObservableScale", ColumnRef]] = None
    abstract_scale: Optional[Union["ObservableScale", ColumnRef]] = None
    group_scale: GroupScaleEnum = GroupScaleEnum.ABSTRACT_SCALE
    tolerance: int | None = None

    def periods(self, df: pd.DataFrame):
        if isref(self.period):
            yield from iter(set(df[self.period.ref]))
        else:
            yield self.period

    def scales(self, df: pd.DataFrame):
        if scale := self.scale:
            if scale.group is None:
                scale.group = self.group
            if isref(scale) and self.abstract_scale is None:
                for p in df[scale.ref].unique():
                    yield p
            elif isref(scale) and isref(self.abstract_scale):
                for _, (sca, abssca) in (
                    df[[scale.ref, self.abstract_scale.ref]]
                    .drop_duplicates()
                    .iterrows()
                ):
                    yield sca, abssca
            elif isref(scale) and not isref(self.abstract_scale):
                for sca in df[scale.ref].unique():
                    yield (sca, self.abstract_scale)
            else:
                yield scale
        else:
            yield from iter([])

    def column_refs(self, independent=True):
        for c in [
            self.id,
            self.name,
            self.description,
            self.parent_id,
            self.group,
            self.period,
            self.geometry,
            self.scale,
            self.abstract_scale,
            self.geometry and (isref(self.geometry) or self.geometry.latitude),
            self.geometry and (isref(self.geometry) or self.geometry.longitude),
        ]:
            if isinstance(c, ColumnRef):
                yield c

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_dict(
            {
                "id": node.id,
                "name": node.name,
                "group": node.group,
                "period": node.period,
                "description": node.description,
                "parent_id": node.parent_id,
                "geometry": node.geometry,
                "obs_class": node.obs_class,
                "scale": node.scale,
                "abstract_scale": node.abstract_scale,
                "group_scale": node.group_scale.value,
            }
        )


class SourceDefinition(BaseModel):
    """Defines the origin and format of raw data for a source."""

    type: Literal["sql", "shape"]
    platform: SourcePlatform
    query: str | None = None    # for type="sql"
    files: list[str] | None = None  # for type="shape"

    @model_validator(mode="after")
    def validate_by_type(self):
        if self.type == "sql" and self.platform == SourcePlatform.GOOGLEDRIVE:
            raise ValueError("platform='googledrive' is not valid for type='sql'")
        if self.type == "shape" and self.platform != SourcePlatform.GOOGLEDRIVE:
            raise ValueError("type='shape' only supports platform='googledrive'")
        return self


class Source(BaseModel):
    yaml_tag: ClassVar = f"!Source"

    slug: str = Field(pattern=SLUG_RE)
    disabled: bool = False
    status: SourceStatus = SourceStatus.READY
    reports: SourceReports | None = None
    description: str
    ref: str
    methodological_notes: str
    retrieve_method: str
    reliability: ReliabilityType
    source: SourceDefinition
    input_encoding: Encodings = Encodings.UTF_8
    output_encoding: Encodings = Encodings.UTF_8
    shape: Shape | None = None
    comment: str
    select: Selection | None = None
    validation: Validation | None = None
    processing: Processing = Processing()
    transform: Transform | None = None
    columns: List[Column] = Field(min_items=1)

    def __hash__(self):
        return hash(self.slug)

    @model_validator(mode="before")
    @classmethod
    def normalize_source_field(cls, data):
        """Converts old format (source_type + source as str/list) to new nested format."""
        if isinstance(data, dict) and "source_type" in data:
            old_type = data.get("source_type")
            old_source = data.get("source")
            if old_source is None or not isinstance(old_source, dict):
                if old_type in ("query", "TODO"):
                    data["source"] = {
                        "type": "sql",
                        "platform": "bigquery",
                        "query": old_source,
                    }
                elif old_type == "shape":
                    files = [old_source] if isinstance(old_source, str) else (old_source or [])
                    data["source"] = {
                        "type": "shape",
                        "platform": "googledrive",
                        "files": files,
                    }
                data.pop("source_type", None)
        return data

    @property
    def source_type(self) -> SourceType:
        """Backward-compat property. Prefer accessing source.type and source.platform directly."""
        if self.source.type == "sql":
            return SourceType.QUERY
        elif self.source.type == "shape":
            return SourceType.SHAPE
        return SourceType.TODO

    @field_validator("columns", mode="before")
    def validate_columns(cls, v):
        return [
            c
            for c in v
            if c.get("status", ColumnStatus.READY)
            in (ColumnStatus.READY, ColumnStatus.VALID)
            and not c.get("disabled", False)
        ]

    def column_refs(self, independent=True):
        for c in self.columns:
            for cf in c.column_refs(independent=independent):
                yield cf

        if self.shape:
            for cf in self.shape.column_refs(independent=independent):
                yield cf

        yield from iter([])

    def periods(self, df: pd.DataFrame):
        yield from iter(set(self.shape.periods(df)))

        for c in self.columns:
            yield from iter(set(c.periods(df)))

    def scales(self, df: pd.DataFrame) -> Iterator[ObservableScale]:
        if validation := self.validation:
            yield from validation.scales(df)
        if select := self.select:
            yield from select.scales(df)
        if shape := self.shape:
            yield from shape.scales(df)
        yield from iter([])

    def get_defaults(self):
        return {c.name: c.default_value for c in self.columns}

    def get_indicators(self, df: pd.DataFrame):
        for c in self.columns:
            yield "/".join(sorted(c.get_dimension_names()))

    def get_obs_groups(self, df: pd.DataFrame):
        return (
            df[self.shape.group.ref].unique()
            if isref(self.shape.group)
            else [self.shape.group]
        )

    @model_validator(mode="after")
    def validate_shape(cls, v):
        assert (
            v.source.type == "shape"
            and v.shape.geometry
            and v.shape.name
            and v.shape.obs_class
        ) or (v.source.type == "sql")
        return v

    @classmethod
    def to_yaml(cls, representer, node):
        source_dict = {
            "type": node.source.type,
            "platform": node.source.platform.value,
        }
        if node.source.query is not None:
            source_dict["query"] = node.source.query
        if node.source.files:
            source_dict["files"] = node.source.files

        return representer.represent_dict(
            {
                "slug": node.slug,
                "status": node.status.value,
                "reports": node.reports,
                "disabled": node.disabled,
                "description": node.description,
                "ref": node.ref,
                "methodological_notes": node.methodological_notes,
                "retrieve_method": node.retrieve_method,
                "comment": node.comment,
                "reliability": node.reliability.value,
                "source": source_dict,
                "shape": node.shape,
                "columns": node.columns,
            }
        )
