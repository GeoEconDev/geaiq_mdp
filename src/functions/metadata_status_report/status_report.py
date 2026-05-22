import functions_framework
from google.cloud import run_v2

PROYECT = "geoecon-dev"
REGION = "us-central1"
JOB = "metadata"


@functions_framework.http
def generar_reporte_cloud_run(request):
    """
    Genera un informe del estado de las ejecuciones de una tarea de Cloud Run.
    """

    # Configura el cliente de Cloud Run.
    client = run_v2.JobsClient()

    # Especifica el nombre del trabajo de Cloud Run.
    job_name = f"projects/{PROYECT}/locations/{REGION}/jobs/{JOB}"  # Reemplaza con tus valores

    try:
        # Obtiene el trabajo de Cloud Run.
        job = client.get_job(name=job_name)

        # Obtiene las ejecuciones del trabajo.
        executions = client.list_executions(parent=job_name)

        # Genera el informe.
        reporte = "Informe de ejecuciones de Cloud Run:\n\n"
        for execution in executions:
            reporte += f"Nombre: {execution.name}\n"
            reporte += f"Estado: {execution.state.name}\n"
            reporte += f"Hora de inicio: {execution.start_time}\n"
            reporte += f"Hora de finalización: {execution.completion_time}\n\n"

        return reporte

    except Exception as e:
        return f"Error al generar el informe: {e}"
