from pathlib import Path
from .gcp import setup_storage

def upload_to_bucket(
    file_path: Path, bucket_name: str, destination_blob_name: str
):
    storage_client = setup_storage()

    # Nombre del archivo local que quieres subir
    local_file_path = str(file_path)

    # Obtén el bucket de Google Cloud Storage
    bucket = storage_client.bucket(bucket_name)

    # Crea un objeto blob para el archivo que deseas subir
    blob = bucket.blob(f"{destination_blob_name}/{file_path.name}")

    # Sube el archivo al bucket
    blob.upload_from_filename(local_file_path)

    blob.make_public()

    return blob.public_url
