import os
import logging
from functools import cache

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/bigquery",
]


@cache
def get_credentials():
    from google.auth import default
    from google.auth.exceptions import DefaultCredentialsError
    try:
        credentials, project = default(scopes=SCOPES)
    except DefaultCredentialsError:
        del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        credentials, project = default(scopes=SCOPES)

    account = getattr(credentials, "account", None) or getattr(credentials, "service_account_email", None)
    logging.info("GCP credentials for project %s by %s", project, account)
    return credentials, project


@cache
def setup_bq():
    from google.cloud import bigquery
    import pandas_gbq
    credentials, project = get_credentials()
    client_bq = bigquery.Client(
        project=project,
        default_query_job_config=bigquery.QueryJobConfig(dry_run=True),
        credentials=credentials,
    )
    pandas_gbq.context.credentials = credentials
    pandas_gbq.context.project = project
    return client_bq


@cache
def setup_ss():
    import gspread
    credentials, _ = get_credentials()
    client_ss = gspread.authorize(credentials)
    return client_ss, credentials.signer_email


@cache
def setup_drive():
    from googleapiclient.discovery import build
    credentials, _ = get_credentials()
    return build("drive", "v3", credentials=credentials)


@cache
def setup_storage():
    from google.cloud import storage
    credentials, project = get_credentials()
    return storage.Client(project=project, credentials=credentials)
