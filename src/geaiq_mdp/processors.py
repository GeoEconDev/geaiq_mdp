from __future__ import annotations
from typing import TYPE_CHECKING

from geaiq_mdp.enums import SourcePlatform, SourceType
from geaiq_mdp.todo import source_type_todo_error

if TYPE_CHECKING:
    from geaiq_mdp.models import Source


def _detect_backend(platform: SourcePlatform) -> str:
    if platform == SourcePlatform.BIGQUERY:
        try:
            import airflow.providers.google.cloud.hooks.bigquery  # noqa: F401
            return "airflow"
        except ImportError:
            return "gcp"
    if platform == SourcePlatform.POSTGRESQL:
        try:
            import airflow.providers.postgres.hooks.postgres  # noqa: F401
            return "airflow"
        except ImportError:
            return "direct"
    return "gcp"


def get_processor(source: Source):
    """Return the appropriate processor instance for a source."""
    source_type = source.source.type
    platform = source.source.platform
    backend = _detect_backend(platform)

    if source_type == "sql" and platform == SourcePlatform.BIGQUERY:
        if backend == "airflow":
            from geaiq_mdp.airflow_bq import AirflowBigQueryProcessor
            return AirflowBigQueryProcessor()
        from geaiq_mdp.bigquery import BigQuerySourceProcessor
        return BigQuerySourceProcessor()

    if source_type == "sql" and platform == SourcePlatform.POSTGRESQL:
        if backend == "airflow":
            from geaiq_mdp.airflow_pg import AirflowPostgreSQLProcessor
            return AirflowPostgreSQLProcessor()
        raise NotImplementedError(
            f"PostgreSQL direct connector not yet implemented. Source: {source.slug}"
        )

    if source_type == "shape" and platform == SourcePlatform.GOOGLEDRIVE:
        from geaiq_mdp.shape import ShapeProcessor
        return ShapeProcessor()

    raise ValueError(
        f"No processor available for type='{source_type}' "
        f"platform='{platform.value}' (source: {source.slug})"
    )


# Kept for backward compatibility — requires geaiq_mdp[gcp] installed.
def _lazy_source_type_processors():
    from geaiq_mdp.bigquery import BigQuerySourceProcessor
    from geaiq_mdp.shape import ShapeProcessor
    return {
        SourceType.TODO:  source_type_todo_error,
        SourceType.QUERY: BigQuerySourceProcessor,
        SourceType.SHAPE: ShapeProcessor,
    }


source_type_processors = None  # use _lazy_source_type_processors() instead
