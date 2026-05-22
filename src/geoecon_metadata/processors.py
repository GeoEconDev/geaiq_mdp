from __future__ import annotations
from typing import TYPE_CHECKING

from geoecon_metadata.enums import SourcePlatform, SourceType
from geoecon_metadata.bigquery import BigQuerySourceProcessor
from geoecon_metadata.shape import ShapeProcessor
from geoecon_metadata.todo import source_type_todo_error

if TYPE_CHECKING:
    from geoecon_metadata.models import Source


class PostgreSQLSourceProcessor:
    """Placeholder — PostgreSQL source processor not yet implemented."""

    def check(self, source, *args, **kwargs):
        raise NotImplementedError(
            f"PostgreSQL source processor is not yet implemented. "
            f"Source: {source.slug}"
        )

    def deploy(self, source, *args, **kwargs):
        raise NotImplementedError(
            f"PostgreSQL source processor is not yet implemented. "
            f"Source: {source.slug}"
        )


_platform_processors = {
    ("sql", SourcePlatform.BIGQUERY):    BigQuerySourceProcessor,
    ("sql", SourcePlatform.POSTGRESQL):  PostgreSQLSourceProcessor,
    ("shape", SourcePlatform.GOOGLEDRIVE): ShapeProcessor,
}

# Kept for backward compatibility with any code that still imports this dict.
source_type_processors = {
    SourceType.TODO:  source_type_todo_error,
    SourceType.QUERY: BigQuerySourceProcessor,
    SourceType.SHAPE: ShapeProcessor,
}


def get_processor(source: Source):
    """Return the appropriate processor instance for a source."""
    key = (source.source.type, source.source.platform)
    processor_cls = _platform_processors.get(key)
    if processor_cls is None:
        raise ValueError(
            f"No processor available for type='{source.source.type}' "
            f"platform='{source.source.platform.value}' (source: {source.slug})"
        )
    return processor_cls()
