from __future__ import annotations
from typing import TYPE_CHECKING
from google.auth import default
from google.api_core.exceptions import Forbidden, NotFound, BadRequest
from geaiq_mdp.enums import Encodings
from .gcp import setup_bq
import pandas_gbq as pdgbq
from time import time
from .processor import ProcessorError, Processor, cache
from pandas_gbq.exceptions import GenericGBQException

if TYPE_CHECKING:
    from .models import Source


class BigQuerySourceProcessor(Processor):
    def __init__(self, **kwargs):
        self.client_bq = None
        self.user = None
        self.project = None
        self.environment = None
        self.geoecon_api = None
        self.report = []
        self.context = None
        super().__init__(**kwargs)

    def setup(self, *args, **kwargs):
        super().setup(*args, **kwargs)
        if not self.client_bq:
            self.client_bq = setup_bq()
            self.user = (
                getattr(self.client_bq._credentials, "account", None)
                or getattr(self.client_bq._credentials, "service_account_email", None)
                or getattr(self.client_bq._credentials, "signer_email", None)
                or "OAuth User Account"
            )
            self.project = self.client_bq.project

    @cache("query", lambda self, source, *args: f"{source.slug}")
    def run_query(self, source: Source):
        source_name = source.slug
        query = source.source.query
        start_time = time()

        try:
            df = pdgbq.read_gbq(query, progress_bar_type=None)
        except GenericGBQException as exc:
            self.report.append(
                {
                    "type": "error",
                    "message": "Generic Big Query Exception",
                    "details": [query, str(exc)],
                }
            )
            raise ProcessorError(exc) from exc
        finally:
            query_time = time() - start_time
            self.report.append(
                {
                    "type": "info",
                    "message": f"Source query {source_name} time",
                    "details": [f"{query_time:0.3f}seg"],
                }
            )
        return df

    def test_source(self, source: Source):
        try:
            query_job = self.client_bq.query(source.source.query)
        except BadRequest as exc:
            self.report.append(
                {"type": "error", "message": "BadRequest query", "details": [str(exc)]}
            )
            return False
        except (Forbidden, NotFound) as exc:
            tables = (
                "\n    *".join(
                    f"{table.project}.{table.dataset_id}.{table.table_id}"
                    for table in exc.query_job.referenced_tables
                )
                or "No tables identified"
            )
            self.report.extend(
                {
                    "type": "error",
                    "message": f"Fails to run query for {source.slug}",
                    "user": self.user,
                    "project": self.project,
                    "details": [
                        f"{err['message']}",
                        f"Check if your query depends on a spreadsheet, and share it with {self.user} if it does",
                        f"Tables: {tables}",
                        f"Query Job: [{exc.query_job.job_id}](https://console.cloud.google.com/bigquery?project={exc.query_job.project}&j={exc.query_job.job_id})",
                        f"Query:\n\n```sql\n{exc.query_job.query}\n```\n",
                    ],
                }
                for err in exc.errors
            )
            return False

        return {
            "estimated_cost": query_job.total_bytes_billed / 1024**3,
            "estimated_total": query_job.total_bytes_processed / 1024**3,
            "retrieved_columns": query_job.schema,
            "retrieved_column_names": [f.name for f in query_job.schema],
            "exists_shape_id": isinstance(source.shape.id, str)
            or (source.shape.id.ref in [f.name for f in query_job.schema]),
            "description": {
                "numerical": {
                    f.name: f.field_type
                    for f in query_job.schema
                    if f.field_type
                    in ("INTEGER", "FLOAT", "NUMERIC", "BOOLEAN", "BIGNUMERIC")
                },
                "strings": {
                    f.name: f.field_type
                    for f in query_job.schema
                    if f.field_type
                    in (
                        "STRING",
                        "BYTES",
                        "TIMESTAMP",
                        "DATE",
                        "TIME",
                        "DATETIME",
                        "GEOGRAPHY",
                        "JSON",
                        "RECORD",
                    )
                },
                "categoricals": {
                    f.name: f.field_type
                    for f in query_job.schema
                    if f.field_type in ("RANGE")
                },
            },
        }
