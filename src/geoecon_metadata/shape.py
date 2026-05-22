from __future__ import annotations
import json
import ssl
from typing import TYPE_CHECKING
from time import time
from pathlib import Path
import re
import logging

from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import numpy as np
from geoecon_metadata.enums import Encodings, Environments
from geoecon_metadata.geoecon_api import GeoEconAPIError
from geoecon_metadata.models.geoecon_api import GeoEconAPIMultipleItems
from geoecon_metadata.models.utils import isref
from geoecon_metadata.processor import EncodingError, Processor, cache, ProcessorError
from geoecon_metadata.gcp import setup_drive
from geoecon_metadata.models import ColumnRef
import zipfile
import geopandas as gpd

from geoecon_metadata.utils import es_legible_unicode


if TYPE_CHECKING:
    from .models import Source


SHAPE_PATH = Path.home() / ".geoecon-shapes"
SHAPE_PATH.mkdir(exist_ok=True)


class DriveMetadataError(ProcessorError):
    message = "Error retrieving metadata from Google Drive"


class ShapeProcessor(Processor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.drive_service = None

    def setup(self, environment=None, context=None):
        super().setup(environment=environment, context=context)
        self.drive_service = setup_drive()

    def download_file(self, file_id, target_dir):
        request = self.drive_service.files().get_media(fileId=file_id)
        try:
            file_metadata = (
                self.drive_service.files()
                .get(fileId=file_id, fields="name", supportsAllDrives=True)
                .execute()
            )
        except ssl.SSLEOFError as exc:
            raise DriveMetadataError({"exception": str(exc), "file_id": file_id})
        except HttpError as exc:
            raise DriveMetadataError(
                {
                    "exception": str(exc),
                    "file_id": file_id,
                    "message": json.loads(exc.content)["error"]["message"],
                    "hint": "Lee el documento README.txt, sección *Preparar ambiente para ejecutar los scripts en Cloud Shell*",
                }
            )

        target_file = target_dir / file_metadata.get("name", file_id)

        if target_file.exists():
            return target_file

        with target_file.open("wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                logging.info(
                    "Downloading %s (%s) %f%%",
                    target_file,
                    file_id,
                    status.progress() * 100,
                )

        return target_file

    @cache("query", lambda self, source, *args: f"{source.slug}")
    def run_query(self, source: Source) -> gpd.DataFrame:
        source_name = source.slug
        files = source.source.files
        input_encoding = source.input_encoding

        temp_dir = SHAPE_PATH / source_name
        temp_dir.mkdir(parents=True, exist_ok=True)

        local_path_list = {}
        for drive_url in files:
            if groups := re.search(r"(/d/|id=)(?P<id>[a-zA-Z0-9_-]+)", drive_url):
                file_id = groups.group("id")
                local_path_list[file_id] = self.download_file(file_id, temp_dir)
            else:
                self.warning("Not valid: {drive_url}")

        for _, fpath in local_path_list.items():
            if fpath.suffix == ".zip":
                with zipfile.ZipFile(fpath, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)

        try:
            shape_file = next(f for f in temp_dir.iterdir() if f.suffix == ".shp")
        except StopIteration:
            return gpd.GeoDataFrame()

        try:
            gdf = gpd.read_file(shape_file, encoding=input_encoding.value)
        except UnicodeDecodeError as err:
            raise EncodingError(
                f"{input_encoding} is invalid. Please try change input encondig to: utf_8, cp850, latin_1, ascii, etc..."
            )

        return gdf

    def test_source(self, source: Source):
        logging.info("Testing source: %s", source.slug)
        data = self.run_query(source)
        if data.empty:
            return False

        return {
            "estimated_cost": 0,
            "estimated_total": data.memory_usage().sum() / 1024**3,
            "retrieved_columns": data.columns,
            "retrieved_column_names": list(data.columns),
            "exists_shape_id": (
                source.shape.id.ref in data.columns
                if isref(source.shape.id)
                else isinstance(source.shape.id, str)
            ),
            "description": {
                "numerical": (
                    data.describe(include=[np.number])
                    if not data.select_dtypes(include=[np.number]).columns.empty
                    else None
                ),
                "strings": (
                    data.describe(include=[object])
                    if not data.select_dtypes(include=[object]).columns.empty
                    else None
                ),
                "categoricals": (
                    data.describe(include=["category"])
                    if not data.select_dtypes(include=["category"]).columns.empty
                    else None
                ),
            },
        }
