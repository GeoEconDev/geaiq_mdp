import os
import logging
from functools import cache
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.cloud import bigquery, storage
from googleapiclient.discovery import build
import gspread
import pandas_gbq

# Define los alcances necesarios para acceder a Google Drive, Google Sheets y BigQuery
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/bigquery",
]


@cache
def get_credentials():
    """
    Obtiene las credenciales predeterminadas de Google Cloud y el ID del proyecto,
    y las actualiza con los alcances necesarios para acceder a Google Drive, Google Sheets y BigQuery.

    Returns:
        Tuple[google.auth.credentials.Credentials, str]: Una tupla que contiene las credenciales
        actualizadas y el ID del proyecto.
    """
    try:
        credentials, project = default(scopes=SCOPES)
    except DefaultCredentialsError:
        del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        credentials, project = default(scopes=SCOPES)
    
    account = getattr(credentials, 'account', None) or getattr(credentials, 'service_account_email', None)
    
    if False and set(SCOPES) - set(credentials.scopes or []):
        raise RuntimeError(f"Not enought required scopes. You have {credentials.scopes}. Expected scopes {SCOPES}.\n"
                           "Please execute following command to enable all these scopes:\n"
                           "gcloud auth application-default login "
                           f"--scopes={','.join(SCOPES)}")
    
    logging.info("GCP credentials for project %s by %s", project, account)
    
    return credentials, project


@cache
def setup_bq():
    """
    Configura y devuelve un cliente de BigQuery utilizando las credenciales y el ID del proyecto obtenidos.

    Returns:
        bigquery.Client: Un cliente de BigQuery configurado con el ID del proyecto y las credenciales obtenidas.
    """
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
    credentials, _ = get_credentials()
    client_ss = gspread.authorize(credentials)
    return client_ss, credentials.signer_email


@cache
def setup_drive():
    credentials, _ = get_credentials()
    drive_service = build("drive", "v3", credentials=credentials)
    return drive_service


@cache
def setup_storage():
    credentials, project = get_credentials()
    client_storage = storage.Client(
        project=project,
        credentials=credentials,
    )
    return client_storage
