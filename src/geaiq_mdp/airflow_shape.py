from __future__ import annotations
from .shape import ShapeProcessor


class AirflowShapeProcessor(ShapeProcessor):
    def __init__(self, slug: str = "", gcp_conn_id: str = "google_cloud_default", **kwargs):
        self.slug = slug
        self.gcp_conn_id = gcp_conn_id
        super().__init__(**kwargs)

    def setup(self, environment=None, context=None):
        # Skip ShapeProcessor.setup() — use Airflow hook instead of setup_drive()
        from geaiq_mdp.processor import Processor
        Processor.setup(self, environment=environment, context=context)
        if not self.drive_service:
            from airflow.providers.google.suite.hooks.drive import GoogleDriveHook
            from geaiq_mdp.airflow_utils import resolve_conn_id
            conn_id = resolve_conn_id(self.slug, self.gcp_conn_id)
            self.drive_service = GoogleDriveHook(gcp_conn_id=conn_id).get_conn()
