from __future__ import annotations
from .shape import ShapeProcessor


class AirflowShapeProcessor(ShapeProcessor):
    def __init__(self, gcp_conn_id: str = "google_cloud_default", **kwargs):
        self.gcp_conn_id = gcp_conn_id
        super().__init__(**kwargs)

    def setup(self, environment=None, context=None):
        # Skip ShapeProcessor.setup() — use Airflow hook instead of setup_drive()
        from geaiq_mdp.processor import Processor
        Processor.setup(self, environment=environment, context=context)
        if not self.drive_service:
            from airflow.providers.google.suite.hooks.drive import GoogleDriveHook
            hook = GoogleDriveHook(gcp_conn_id=self.gcp_conn_id)
            self.drive_service = hook.get_conn()
