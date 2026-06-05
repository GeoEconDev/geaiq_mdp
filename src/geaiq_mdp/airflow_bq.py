from __future__ import annotations
from typing import TYPE_CHECKING
from time import time
from .processor import Processor, cache, ProcessorError

if TYPE_CHECKING:
    from .models import Source


class AirflowBigQueryProcessor(Processor):
    def __init__(self, gcp_conn_id: str = "google_cloud_default", **kwargs):
        self.gcp_conn_id = gcp_conn_id
        self.hook = None
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
        if not self.hook:
            from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
            self.hook = BigQueryHook(gcp_conn_id=self.gcp_conn_id)
            self.client_bq = self.hook.get_client()
            self.project = self.hook.project_id
            self.user = self.gcp_conn_id

    @cache("query", lambda self, source, *args: f"{source.slug}")
    def run_query(self, source: Source):
        source_name = source.slug
        query = source.source.query
        start_time = time()

        try:
            df = self.hook.get_pandas_df(sql=query)
        except Exception as exc:
            self.report.append(
                {
                    "type": "error",
                    "message": "BigQuery Exception",
                    "details": [query, str(exc)],
                }
            )
            raise ProcessorError(exc) from exc
        finally:
            self.report.append(
                {
                    "type": "info",
                    "message": f"Source query {source_name} time",
                    "details": [f"{time() - start_time:0.3f}seg"],
                }
            )
        return df

    def test_source(self, source: Source):
        from google.api_core.exceptions import Forbidden, NotFound, BadRequest
        from google.cloud.bigquery import QueryJobConfig
        job_config = QueryJobConfig(dry_run=True, use_query_cache=False)
        try:
            query_job = self.client_bq.query(source.source.query, job_config=job_config)
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
                    if f.field_type in ("INTEGER", "FLOAT", "NUMERIC", "BOOLEAN", "BIGNUMERIC")
                },
                "strings": {
                    f.name: f.field_type
                    for f in query_job.schema
                    if f.field_type in (
                        "STRING", "BYTES", "TIMESTAMP", "DATE", "TIME",
                        "DATETIME", "GEOGRAPHY", "JSON", "RECORD",
                    )
                },
                "categoricals": {
                    f.name: f.field_type
                    for f in query_job.schema
                    if f.field_type in ("RANGE",)
                },
            },
        }
