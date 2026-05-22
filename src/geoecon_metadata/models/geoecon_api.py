from typing import Any, ClassVar
from pydantic import BaseModel
import logging

from requests import HTTPError


class GeoEconAPIError(Exception):
    message = "Error"
    
    def __init__(self, class_, request_payload, response_payload):
        self.class_ = class_
        self.request_payload = request_payload
        self.response_payload = response_payload
        
    def str(self):
        return f"{self} on {self.class_.name}. Request: {self.request_payload}. Response: {self.response_payload}"


class GeoEconAPIMultipleItems(GeoEconAPIError):
    message = "Multiple items error"


class GeoEconAPIUnexpectedError(GeoEconAPIError):
    message = "Unexpected error"


class GeoEconAPIModel(BaseModel):
    geoecon_api_endpoint: ClassVar = None

    def geoecon_api_key(self, geoecon_api: Any) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def __map_slug__(self, map: dict[str, Any]) -> str:
        raise NotImplementedError

    def __slug__(self) -> str:
        raise NotImplementedError

    def geoecon_api_data(self) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def __api_get_all(cls, geoecon_api: Any = None):
        if cls.geoecon_api_endpoint is None:
            raise ValueError(
                "Please setup geoecon_api_endpoint for {self.__class__.__name__}"
            )

        return geoecon_api.list(cls.geoecon_api_endpoint)

    def __api_get(self, geoecon_api: Any = None):
        if self.geoecon_api_endpoint is None:
            raise ValueError(
                "Please setup geoecon_api_endpoint for {self.__class__.__name__}"
            )

        keys = self.geoecon_api_key(geoecon_api)
        class_name = self.__class__.__name__

        if data := geoecon_api.get(self.geoecon_api_endpoint, params=keys):
            if data["total"] == 1:
                logging.debug(f"API returns one item of  %s: %s", class_name, keys)
                return self.model_copy(update=data["items"][0])
            elif data["total"] > 1:
                logging.error(
                    "API returns more than one item of %s: %s",
                    class_name,
                    keys,
                )
                raise GeoEconAPIMultipleItems(self.__class__, keys, data)
            else:
                logging.warning("API returns zero itemsof %s: %s", class_name, keys)
                return None

    def __api_update(self, geoecon_api: Any):
        if data := geoecon_api.post(
            f"{self.geoecon_api_endpoint}/{self.uuid}", json=self.geoecon_api_data()
        ):
            logging.debug(
                f"API update one item of {self.__class__.__name__}: {self.geoecon_api_key()}"
            )
            return self.model_copy(update=data)
        else:
            logging.error(
                f"Something goes wrong with %s: %s",
                self.__class__.__name__,
                self.geoecon_api_key(),
            )
            raise GeoEconAPIUnexpectedError(self.__class__, self.geoecon_api_data(), data)


    def __api_create(self, geoecon_api: Any):
        if data := geoecon_api.post(
            self.geoecon_api_endpoint, json=self.geoecon_api_data()
        ):
            logging.debug(
                f"API create one item of {self.__class__.__name__}: {self.geoecon_api_key()}"
            )
            return self.model_copy(update=data)
        else:
            logging.error(
                f"Something goes wrong with %s: %s",
                self.__class__.__name__,
                self.geoecon_api_key(),
            )
            raise GeoEconAPIUnexpectedError(self.__class__, self.geoecon_api_data(), data)


    def get(self, geoecon_api):
        return self.__api_get(geoecon_api)

    def update(self, geoecon_api: Any):
        return self.__api_update(geoecon_api)

    def create(self, geoecon_api: Any):
        if r := self.__api_get(geoecon_api):
            return r
        return self.__api_create(geoecon_api)

    def subitems(self):
        return iter([])

    @classmethod
    def create_lst(cls, geoecon_api, item_list):
        data = cls.__api_get_all(geoecon_api)
        item_map = {item.__slug__(): item for item in item_list}
        for item in data:
            item_key = cls.__map_slug__(item)
            if item_key in item_map:
                item_map[item_key].model_copy(update=item)

        return item_list
