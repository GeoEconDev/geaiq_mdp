import functools
import tracemalloc
from time import time, perf_counter
from datetime import datetime, timedelta
import logging
import unicodedata
from urllib.parse import urlencode, quote
import os
import requests


def compare_dicts(dict1, dict2, tolerance=0.1):
    """
    Compara dos diccionarios, considerando un error relativo aceptable para números flotantes.

    Args:
        dict1 (dict): Primer diccionario.
        dict2 (dict): Segundo diccionario.
        tolerance (float): Tolerancia relativa aceptable para flotantes (por defecto 10%).

    Returns:
        bool: True si los diccionarios son equivalentes, False en caso contrario.
    """
    if dict1.keys() != dict2.keys():
        return False

    for key in dict1:
        val1, val2 = dict1[key], dict2[key]

        # Comparación para flotantes con tolerancia
        if isinstance(val1, float) and isinstance(val2, float):
            if not abs(val1 - val2) <= tolerance * max(abs(val1), abs(val2)):
                return False

        elif isinstance(val1, dict) and isinstance(val2, dict):
            return compare_dicts(val1, val2, tolerance)

        # Comparación directa para otros tipos
        elif val1 != val2:
            return False

    return True


def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def drop_duplicates(items: list):
    return [item for i, item in enumerate(items) if item not in items[:i]]


def memory_time_logger(func):
    """Decorador para medir el uso de memoria y el tiempo de ejecución de una función sin reiniciar tracemalloc si ya está activo"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        is_tracemalloc_running = (
            tracemalloc.is_tracing()
        )  # Verificar si tracemalloc ya está activo

        if not is_tracemalloc_running:
            tracemalloc.start()  # Iniciar el rastreo solo si no estaba activo

        start_time = perf_counter()  # Tiempo inicial

        result = func(*args, **kwargs)  # Ejecutar la función decorada

        end_time = perf_counter()  # Tiempo final
        current, peak = tracemalloc.get_traced_memory()  # Obtener uso de memoria

        execution_time = end_time - start_time  # Calcular tiempo de ejecución

        logging.info(
            "[%s] Execution time: %.4f s | Memory usage: %.2f GB | Peak usage: %.2f GB",
            func.__name__,
            execution_time,
            current / (1024**3),
            peak / (1024**3),
        )

        if not is_tracemalloc_running:
            tracemalloc.stop()  # Solo detener si esta función lo inició

        return result

    return wrapper


def es_legible_unicode(texto):
    for char in texto:
        categoria = unicodedata.category(char)
        if categoria.startswith("C"):  # "C" = Control, "Cf" = Formato, "Co" = Privado
            return False
        if categoria == "No":
            return False
    return True


def get_region():
    url = "http://metadata.google.internal/computeMetadata/v1/instance/region"
    headers = {"Metadata-Flavor": "Google"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text.split("/")[-1]  # Extraer solo la región
    return None


def seconds_to_iso8601_duration(seconds: int) -> str:
    td = timedelta(seconds=seconds)
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    duration = "P"
    if days:
        duration += f"{days}D"
    if hours or minutes or seconds:
        duration += "T"
        if hours:
            duration += f"{hours}H"
        if minutes:
            duration += f"{minutes}M"
        if seconds:
            duration += f"{seconds}S"

    return duration


def url_to_logs(timestamp: datetime, duration: int = 24 * 60 * 60):
    url_base = "https://console.cloud.google.com/logs/query"
    query = [
        ("resource.type", "=", "cloud_run_job"),
        ("resource.labels.job_name", "=", os.getenv("CLOUD_RUN_JOB")),
        (
            'labels."run.googleapis.com/execution_name"',
            "=",
            os.getenv("CLOUD_RUN_EXECUTION"),
        ),
        ("resource.labels.location", "=", "us-central1"),
        (
            'labels."run.googleapis.com/task_index"',
            "=",
            os.getenv("CLOUD_RUN_TASK_INDEX"),
        ),
        ("severity", ">=", "DEFAULT"),
    ]
    query_str = " ".join(
        f"{key} {operator} \"{value}\"" for key, operator, value in query
    )
    url_query = urlencode(
        {
            "query": query_str,
            "storageScope": "project",
            "cursorTimestamp": timestamp.replace(tzinfo=None).isoformat(timespec="microseconds") + "Z",
            "duration": seconds_to_iso8601_duration(duration),
            "invt": "AbscqA",
            "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
        },
        quote_via=quote
    ).replace('&', ';')
    return f"{url_base};{url_query}"
