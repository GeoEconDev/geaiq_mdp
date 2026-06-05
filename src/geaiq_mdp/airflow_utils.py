from __future__ import annotations
import logging


def resolve_conn_id(slug: str, default: str) -> str:
    """Return mdp.<slug> if that Airflow connection exists, otherwise default."""
    mdp_conn_id = f"mdp.{slug}"
    try:
        from airflow.models import Connection
        Connection.get_connection_from_secrets(mdp_conn_id)
        logging.info("Using Airflow connection %s for source %s", mdp_conn_id, slug)
        return mdp_conn_id
    except Exception:
        return default
