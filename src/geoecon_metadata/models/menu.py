from typing import ClassVar, List, Optional
from pydantic import BaseModel, model_validator
from slugify import slugify
from requests import HTTPError

from .utils import IncludeOptions
from .dimension import Dimension
from .source import ObservableGroup


class MenuSelection(BaseModel):
    yaml_tag: ClassVar = f"!MenuSelection"

    shape_groups: List[ObservableGroup] = []
    dimensions: List[Dimension] = []


class MenuOption(BaseModel):
    yaml_tag: ClassVar = f"!MenuOption"

    name: str
    slug: str | None = None
    scope: str = "openning"
    description: str
    select: Optional[MenuSelection] = None
    options: Optional[List["MenuOption"]] = None
    debug: bool = False


    @model_validator(mode="before")
    def set_slug(cls, values: dict):
        if not values.get("slug") and "name" in values:
            values["slug"] = slugify(values["name"])
        return values

    def optioniter(self, parents=None):
        new_parents = (parents or []) + [self]

        if self.options is None:
            yield new_parents
        else:
            for o in self.options:
                for so in o.optioniter(new_parents):
                    yield so

    def iter(self):
        yield self

        if self.options is None:
            return

        for o in self.options:
            for so in o.iter():
                yield so

    def upload_tag(self, geoecon_api, uuid=None):
        try:
            if data := geoecon_api.post(
                "ui/tags",
                json={
                    "name": self.name,
                    "code": self.slug,
                    "description": self.description,
                    "tag_scopes": [{"code": self.scope}],
                },
            ):
                print(f"{self.name} [{self.scope}] Created as [{data['uuid']}]")
        except HTTPError as exc:
            if exc.response.status_code == 409 and uuid:
                data = geoecon_api.post(
                    f"ui/tags/{uuid}",
                    json={
                        "name": self.name,
                        "code": self.slug,
                        "description": self.description,
                    },
                )
                print(f"{self.name} [{self.scope}]:{data['uuid']} Updated")
            elif exc.response.status_code == 409:
                print("Needs update but doesnt have uuid")
            else:
                print(f"Error {exc.response.content}")
