from datetime import date
import os
from uuid import UUID
import io
import pandas as pd
import requests
from pathlib import Path
from requests.adapters import HTTPAdapter, Retry
from requests.compat import urljoin
import logging

from .models import (
    Class_,
    Source,
    Period,
)
from .models.utils import isref
from .enums import SCALE_TO_DETAILS, Environments
from urllib.parse import urlparse


class ObservableNotFound(Exception):
    def __init__(self, observable_name):
        super().__init__(observable_name)


class DataError(Exception):
    def __init__(self, instance_uuid, error):
        super().__init__(instance_uuid, error)

    def __str__(self):
        return f"uuid:{self.args[0]}:{self.args[1]}"


class GeometryUploadingError(Exception):
    def __init__(self, instance_uuid, error):
        super().__init__(instance_uuid, error)

    def __str__(self):
        return f"uuid:{self.args[0]}:{self.args[1]}"


class GeoEconAPIError(Exception):
    message = "GeoEcon API raises an error"

    def __init__(self, *details):
        self.details = details

    def __str__(self):
        return f"{type(self).__name__}:{self.message}"

    def report(self):
        return {
            "typo": "error",
            "message": self.message or "No message",
            "details": self.details,
        }


def final_slash(url):
    if not url.endswith("/"):
        url += "/"
    return url


class GeoEconAPI:
    static_uri: str | None = None
    api_uri: str | None = None

    def __init__(self):
        self.session: requests.Session = requests.Session()
        assert self.api_uri is not None, "Abstract API client"

        retries = Retry(
            total=5,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504],
            redirect=True,
        )
        self.session.mount(
            f"{urlparse(self.api_uri).scheme}://", HTTPAdapter(max_retries=retries)
        )
        self.session.headers.update({'User-Agent': os.getenv('USER_AGENT', 'Metadata Processor')})

        token = os.getenv('GEAIQ_API_TOKEN')
        if not token:
            user = os.getenv('GEAIQ_API_USER')
            password = os.getenv('GEAIQ_API_PASSWORD')
            if user and password:
                token = self._login(user, password)
        if token:
            self.session.headers.update({'Authorization': f'Bearer {token}'})

    def _login(self, username: str, password: str) -> str:
        resp = self.session.post(
            urljoin(self.api_uri, 'auth/token'),
            data={'username': username, 'password': password},
        )
        resp.raise_for_status()
        return resp.json()['access_token']

    def list(self, endpoint, *args, **kwargs):
        page = 1
        last_page = 2
        while page <= last_page:
            data = self.get(
                urljoin(self.api_uri, endpoint), *args, params={**kwargs, "page": page}
            )
            for item in data["items"]:
                yield item
            page += 1
            last_page = data["pages"]

    def get(self, endpoint, *args, **kwargs):
        result = self.session.get(urljoin(self.api_uri, endpoint), *args, **kwargs)
        result.raise_for_status()
        return result.json()

    def post(self, endpoint, add_final_slash=True, *args, **kwargs):
        url = urljoin(self.api_uri, endpoint)
        if add_final_slash:
            url = final_slash(url)
        result = self.session.post(url, *args, **kwargs)

        if result.status_code >= 400:
            try:
                error_msg = result.json()["detail"]
            except requests.exceptions.JSONDecodeError:
                error_msg = result.text
            logging.error("GeoEcon Api Error: %s", error_msg)

        result.raise_for_status()
        return result.json()

    def delete(self, endpoint, *args, **kwargs):
        result = self.session.delete(urljoin(self.api_uri, endpoint), *args, **kwargs)
        result.raise_for_status()
        return result.json()

    def get_observables_by_group(
        self,
        uuid: UUID | None = None,
        name: str | None = None,
        period: str | None = None,
    ):
        if name:
            data = self.get(
                f"wh/observables/groups",
                params={"name": name, "uuid": str(uuid) if uuid else None},
            )
            if data and "items" in data and data["items"]:
                uuid = data["items"][0]["uuid"]
            else:
                raise ObservableNotFound(name)

        return self.list(
            f"wh/observables/groups/{str(uuid)}/observables", period=period
        )

    # Sources
    def get_source(self, source: Source):
        data = self.get("wh/sources", params={"name": source.slug})
        if data["total"]:
            logging.info("Get source %s (%s)", source.slug, data["items"][0]["uuid"])
            return data["items"][0]
        return None

    def new_source(self, source: Source):
        new_source = {
            "name": source.slug,
            "description": source.description,
            "comment": source.comment,
            "method": source.retrieve_method,
            "reliability": source.reliability.value,
        }
        try:
            data = self.post("wh/sources", json=new_source)
            logging.info("New source %s (%s)", source.slug, data["uuid"])
            return data
        except requests.exceptions.HTTPError as err:
            if err.response.status_code >= 400:
                logging.error("GeoEcon Api Error: %s", err.response.json()["detail"])
            raise GeoEconAPIError(err.response.json()["detail"])

    # Periods
    def get_period(self, name: str):
        data = self.get("wh/periods", params={"name": name})
        if data["total"]:
            logging.info("Get period %s (%s)", name, data["items"][0]["uuid"])
            return data["items"][0]
        return None

    def new_period(self, name: str, start_date: date, end_date: date, description: str):
        new_period = {
            "name": str(name),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "description": str(description),
        }
        data = self.post("wh/periods", json=new_period)
        logging.info("New period %s (%s)", name, data["uuid"])
        return data

    def update_period(
        self, uuid: str, name: str, start_date: date, end_date: date, description: str
    ):
        raise NotImplementedError

    def get_periods(self, source: Source, df: pd.DataFrame):
        return {p: self.get_period(p) for p in set(source.periods(df))}

    def sync_period(self, period: Period, sync="to_db"):
        assert period.name is not None, "Period update requires assigned name"
        data = self.get_period(period.name) or self.new_period(
            period.name, period.start_date, period.end_date, period.description
        )
        assert data, "Expected created period"
        assert (
            period.uuid is None or period.uuid == data["uuid"]
        ), "Expected empty uuid or equal uuid from db"

        if period.uuid is None:
            period.uuid = data["uuid"]

        if sync == "from_db":
            period.name = data["name"]
            period.description = data["description"]
            period.start_date = data["start_date"]
            period.end_date = data["end_date"]
        else:
            data["name"] = period.name
            data["description"] = period.description
            data["start_date"] = period.start_date
            data["end_date"] = period.end_date
            self.update_period(
                period.uuid,
                period.name,
                period.start_date,
                period.end_date,
                period.description,
            )

    # Classes
    def get_class(self, name: str, typo: str):
        data = self.get("wh/classes", params={"name": name, "type": typo})
        if data["total"]:
            logging.info("Get class %s (%s)", name, data["items"][0]["uuid"])
            return data["items"][0]
        return None

    def new_class(self, name, typo, description):
        new_class = {
            "name": name,
            "type": typo,
            "description": description,
        }
        try:
            data = self.post("wh/classes/", json=new_class)
            logging.info("New class %s (%s)", name, data["uuid"])
            return data
        except requests.exceptions.HTTPError as err:
            if err.response.status_code >= 400:
                logging.error("GeoEcon Api Error: %s", err.response.json()["detail"])
        return None

    def update_class(self, uuid, name, typo, description):
        raise NotImplementedError

    def sync_class(self, cls: Class_, sync="to_db"):
        assert cls.name is not None, "Class update requires assigned name"
        data = self.get_class(cls.name, cls.typo) or self.new_class(
            cls.name, cls.typo, cls.description
        )
        assert data, "Expected created class"
        assert (
            cls.uuid is None or cls.uuid == data["uuid"]
        ), "Expected empty uuid or equal uuid from db"

        if cls.uuid is None:
            cls.uuid = data["uuid"]

        if sync == "from_db":
            cls.name = data["name"]
            cls.description = data["description"]
            cls.typo = data["type"]
        else:
            data["name"] = cls.name
            data["description"] = cls.description
            data["type"] = cls.typo
            self.update_class(cls.uuid, cls.name, cls.typo, cls.description)

    # Attributes
    def get_attribute(self, name: str):
        data = self.get("wh/attributes", params={"name": name})
        if data["total"]:
            logging.info("Get attribute %s (%s)", name, data["items"][0]["uuid"])
            return data["items"][0]
        return None

    def new_attribute(self, name: str, unit: str, parent_uuid: str, description: str):
        new_attribute = {
            "name": name,
            "unit": unit,
            "description": description,
            "parent_uuid": parent_uuid,
        }
        data = self.post("wh/attributes", json=new_attribute)
        logging.info("New attribute %s (%s)", name, data["uuid"])
        return data

    # Topics
    def get_topic(self, name: str):
        data = self.get("ui/topics", params={"code": name})
        if data["total"]:
            logging.info("Get topic %s (%s)", name, data["items"][0]["uuid"])
            return data["items"][0]
        return None

    def new_topic(
        self, name: str, order: int, help: str, icon: str, code: str, description: str
    ):
        new_topic = {
            "code": code,
            "icon": icon,
            "help": help,
            "order": order,
            "name": name,
            "description": description,
        }
        data = self.post("ui/topics", json=new_topic)
        logging.info("New topic %s (%s)", name, data["uuid"])
        return data

    # Observables class
    def get_obs_class(self, name: str):
        data = self.get("wh/observables/classes", params={"name": name})
        if data["total"]:
            logging.info("Get obs class %s (%s)", name, data["items"][0]["uuid"])
            return data["items"][0]
        return None

    def new_obs_class(self, name: str):
        new_class = {
            "name": name,
        }
        data = self.post("wh/observables/classes", json=new_class)
        logging.info("New obs class %s (%s)", name, data["uuid"])
        return data

    # Observables group
    def get_obs_group(self, name: str):
        data = self.get("wh/observables/groups", params={"name": name})
        if data["total"]:
            logging.info("Get obs group %s (%s)", name, data["items"][0]["uuid"])
            return data["items"][0]
        return None

    def new_obs_group(self, name: str, typo: str, description: str):
        new_group = {"name": name, "type": typo, "description": description}
        data = self.post("wh/observables/groups", json=new_group)
        logging.info("New obs group %s (%s)", name, data["uuid"])
        return data

    # Observables scales
    def get_obs_scale(self, name: str, group: str | None):
        group_dict = {"name": group} if group else {}
        data = self.get(
            "wh/observables/scales",
            params={"name": name, **group_dict},
        )
        if data["total"]:
            logging.info(
                "Get obs scale %s (%s)",
                data["items"][0]["name"],
                data["items"][0]["uuid"],
            )
            return data["items"][0]
        return None

    def new_obs_scale(
        self,
        name: str,
        description: str,
        typo: str,
        group: str | None = None,
        abstract_scale: str | None = None,
    ):
        new_scale = {
            "name": name,
            "description": description,
            "group": {"name": group},
            "type": typo,
            "abstract_scale": {"name": abstract_scale},
        }
        data = self.post("wh/observables/scales", json=new_scale)
        logging.info("New obs scale %s (%s)", data["name"], data["uuid"])
        return data

    def get_obs_scales(self, source: Source, data: pd.DataFrame):
        if isref(source.shape.scale):
            breakpoint()
        else:
            scales = [source.shape.scale]

        scales = {
            s
            for s in set(
                data[source.shape.scale.ref].unique()
                if isref(source.shape.scale)
                else ([source.shape.scale.value] if source.shape.scale else [])
            )
        } | set(
            [s.value for s in scales]
            if (val := source.validation)
            and (obs := val.observables)
            and (scales := obs.shape_scale)
            else []
        )
        return {s: self.get_obs_scale(s) for s in scales}

    # Observables
    def get_observables(self, period_uuid: str, group_uuid: str, **_):
        data = self.get(
            f"wh/observables/groups/{group_uuid}/observables",
            params={
                "period_uuid": period_uuid,
            },
        )
        if data["total"]:
            logging.info(
                "Get %i observables from group %s (%s) and period %s (%s)",
                data["total"],
                data["items"][0]["group"]["name"],
                data["items"][0]["group"]["uuid"],
                data["items"][0]["period"]["name"],
                data["items"][0]["period"]["uuid"],
            )
            return data["items"]
        else:
            None

    def get_observable(
        self, group_id: str, period_uuid: str, group_uuid: str, source_uuid: str, **_
    ):
        data = self.get(
            "wh/observables",
            params={
                "group_id": group_id,
                "period_uuid": period_uuid,
                "group_uuid": group_uuid,
                "source_uuid": source_uuid,
            },
        )
        if data["total"]:
            logging.info(
                "Get observable %s:%s [%s] (%s)",
                data["items"][0]["name"],
                data["items"][0]["group_id"],
                data["items"][0]["period"]["uuid"],
                data["items"][0]["uuid"],
            )
            return data["items"][0]
        else:
            None

    def new_observable(
        self,
        reliability: str,
        class_uuid: str,
        scale_uuid: str,
        period_uuid: str,
        group_uuid: str,
        source_uuid: str,
        group_id: str,
        group_parent_id: str,
        name: str,
        description: str,
        geometry: str,
    ):
        new_observation = {
            "reliability": reliability,
            "class_uuid": class_uuid,
            "scale_uuid": scale_uuid,
            "period_uuid": period_uuid,
            "group_uuid": group_uuid,
            "source_uuid": source_uuid,
            "group_id": group_id,
            "group_parent_id": group_parent_id,
            "name": name,
            "description": description,
        }
        new_obs = self.post("wh/observables", json=new_observation)
        logging.info(
            "New observable %s:%s [%s] (%s)",
            new_obs["name"],
            new_obs["group_id"],
            new_obs["period_uuid"],
            new_obs["uuid"],
        )
        return new_obs

    def upload_geometry(self, geometry_uuid: str, geometry: str):
        logging.info(f"Uploading geometry instance {geometry_uuid}.")
        try:
            return self.post(
                f"wh/observables/{geometry_uuid}/geometry", files={"geometry": geometry}
            )
        except requests.exceptions.HTTPError as exc:
            raise GeometryUploadingError(geometry_uuid, str(exc))

    # Indicator
    def get_indicator(self, code):
        data = self.get("ui/indicators", params={"code": code})
        if data["total"]:
            logging.info(
                "Get indicator %s (%s)",
                data["items"][0]["name"],
                data["items"][0]["uuid"],
            )
            return data["items"][0]
        else:
            None

    def new_indicator(self, name, code, description, attribute):
        new_indicator = {
            "code": code,
            "icon": f"{code}.png",
            "help": description,
            "opening": "no opening",
            "cluster_algorithm": "Any",
            "instances": [],
            "attribute": {"name": attribute},
            "order": 1,
            "topics": [{"code": "notopic"}],
            "name": name,
            "description": description,
        }
        try:
            data = self.post("ui/indicators/", json=new_indicator)
            logging.info("New indicator %s (%s)", name, data["uuid"])
            return data
        except requests.exceptions.HTTPError as err:
            if err.response.status_code >= 400:
                logging.error("GeoEcon Api Error: %s", err.response.json()["detail"])

    # Instance full data
    def get_instance(self, uuid):
        data = self.get(f"ui/instances/{uuid}")
        if data:
            logging.info(
                "Get instance %s (%s)",
                data["name"],
                data["uuid"],
            )
            return data

        return None

    # Instances by code
    def get_instance_by_code(self, code):
        instance_indicator = {
            "code": code,
        }

        data = self.get("ui/instances", params=instance_indicator)
        if data["total"]:
            logging.info(
                "Get instance %s (%s)",
                data["items"][0]["name"],
                data["items"][0]["uuid"],
            )
            return data["items"][0]

        return None

    def new_instance(
        self,
        name: str,
        code: str,
        indicator_code: str,
        scale: str,
        class_name: str,
        class_type: str,
        shape_period: str,
        data_period: str,
        shape_group: str,
        source_slug: str,
    ):
        new_instance_indicator = {
            "name": name,
            "code": code,
            "indicator": {"code": indicator_code},
            "scale": {"name": scale, "group": None, "abstract_scale": None},
            "class": {"name": class_name, "type": class_type},
            "period": {"name": shape_period},
            "data_period": {"name": data_period},
            "group": {"name": shape_group},
            "status": "draft",
            "source": {"name": source_slug},
        }
        logging.info("Post instance indicator:\n"+str(new_instance_indicator))
        try:
            return self.post("ui/instances/", json=new_instance_indicator)
        except requests.exceptions.ConnectionError as err:
            logging.error("GeoEcon Api Error: %s", err)
            raise GeoEconAPIError(f"{err}")
        except requests.exceptions.HTTPError as err:
            if err.response.status_code >= 400:
                logging.error("GeoEcon Api Error: %s", err.response.text)
            raise GeoEconAPIError(f"{err.response.text}")

    def get_instances(
        self,
        uuid=None,
        name=None,
        code=None,
        indicator_uuid=None,
        class_uuid=None,
        data_period_uuid=None,
        group_uuid=None,
        period_uuid=None,
        scale_uuid=None,
        source_uuid=None,
    ):
        instance_indicator = {
            k: v
            for k, v in {
                "uuid": uuid,
                "name": name,
                "code": code,
                "indicator_uuid": indicator_uuid,
                "class_uuid": class_uuid,
                "data_period_uuid": data_period_uuid,
                "group_uuid": group_uuid,
                "period_uuid": period_uuid,
                "scale_uuid": scale_uuid,
                "source_uuid": source_uuid,
            }.items()
            if v is not None
        }

        page = None
        while (
            data := self.get(
                "ui/instances", params={**instance_indicator, "page": page}
            )
        ) and data["items"]:
            for item in data["items"]:
                yield item
            page = data["page"] + 1

    def del_instances(self, uuid):
        self.delete(f"ui/instances/{str(uuid)}/")

    def del_data_instances(self, uuid):
        self.delete(f"ui/instances/{str(uuid)}/data")

    def update_instance(self, uuid: UUID, df: pd.DataFrame):
        try:
            with io.BytesIO() as ostream:
                df.to_parquet(ostream)
                ostream.seek(0)
                return self.post(
                    f"ui/instances/{str(uuid)}/data", files={"data": ostream}
                )
        except requests.exceptions.HTTPError as err:
            if (err.response.status_code == 400) and (
                detail := err.response.json().get("detail", None)
            ):
                raise DataError(uuid, detail)
        pass

    def upload_report(self, step: str, status: str, file_path: Path, run_uuid: str = None):
        if run_uuid:
            endpoint = f"r/{step}/run/{run_uuid}"
            public_path = f"reports/{step}/run/{run_uuid}/{file_path.name}"
        else:
            endpoint = f"r/{step}/{status}"
            public_path = f"reports/{step}/{status}/{file_path.name}"
        with open(file_path, "rb") as file_data:
            files = {"file": (file_path.name, file_data)}
            message = self.post(endpoint, add_final_slash=False, files=files)
        if message['message']:
            return self.static_uri + public_path
        logging.warning("Report upload failed with %s", message)
        return None

class GeoEconAPIDev(GeoEconAPI):
    _api_base = os.environ.get("GEAIQ_API_URL", "https://api.geaiq.com/").rstrip("/") + "/"
    static_uri = os.environ.get("GEAIQ_API_PUBLIC_URL", _api_base.rstrip("/")).rstrip("/") + "/"
    api_uri = _api_base + "api/v1/"


class GeoEconAPIProd(GeoEconAPI):
    _api_base = os.environ.get("GEAIQ_API_URL", "https://api.geaiq.com/").rstrip("/") + "/"
    static_uri = os.environ.get("GEAIQ_API_PUBLIC_URL", _api_base.rstrip("/")).rstrip("/") + "/"
    api_uri = _api_base + "api/v1/"


class GeoEconAPILocal(GeoEconAPI):
    static_uri = "http://localhost:8000/"
    api_uri = static_uri + "api/v1/"


class GeoEconAPITest(GeoEconAPI):
    def __init__(self):
        pass


GEOECON_API_MAP: dict[Environments, GeoEconAPI] = {
    Environments.DEV: GeoEconAPIDev,
    Environments.PROD: GeoEconAPIProd,
    Environments.LOCAL: GeoEconAPILocal,
    Environments.TEST: GeoEconAPITest,
}
