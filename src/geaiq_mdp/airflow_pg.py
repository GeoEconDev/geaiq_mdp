from __future__ import annotations
from typing import TYPE_CHECKING
from time import time
from .processor import Processor, cache, ProcessorError

if TYPE_CHECKING:
    from .models import Source


class AirflowPostgreSQLProcessor(Processor):
    def __init__(self, slug: str = "", postgres_conn_id: str = "postgres_staging", **kwargs):
        self.slug = slug
        self.postgres_conn_id = postgres_conn_id
        self.hook = None
        self.user = None
        self.environment = None
        self.geoecon_api = None
        self.report = []
        self.context = None
        super().__init__(**kwargs)

    def setup(self, *args, **kwargs):
        super().setup(*args, **kwargs)
        if not self.hook:
            from airflow.providers.postgres.hooks.postgres import PostgresHook
            from geaiq_mdp.airflow_utils import resolve_conn_id
            conn_id = resolve_conn_id(self.slug, self.postgres_conn_id)
            self.hook = PostgresHook(postgres_conn_id=conn_id)
            self.user = self.postgres_conn_id

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
                    "message": "PostgreSQL Exception",
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
        try:
            conn = self.hook.get_conn()
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN {source.source.query}")
            plan = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as exc:
            self.report.append(
                {"type": "error", "message": "PostgreSQL query error", "details": [str(exc)]}
            )
            return False

        return {
            "estimated_cost": 0,
            "estimated_total": 0,
            "retrieved_columns": [],
            "retrieved_column_names": [],
            "exists_shape_id": True,
            "description": {"plan": plan},
        }
