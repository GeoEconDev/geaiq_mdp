from pathlib import Path
from googleapiclient.http import MediaFileUpload
from geoecon_metadata.gcp import setup_drive


def get_drive_id(shared_drive_name):
    """
    Retrieves the ID of a shared Google Drive by its name.

    Args:
        shared_drive_name (str): The name of the shared Drive.

    Returns:
        str: The ID of the shared Drive.

    Raises:
        RuntimeError: If the shared Drive is not found.
    """
    service = setup_drive()

    response = service.drives().list(fields="drives(id, name)").execute()

    for drive in response.get("drives", []):
        if drive["name"] == shared_drive_name:
            return drive["id"]

    raise RuntimeError(f"Drive {shared_drive_name} not found")


def query_folder_id(service, drive_path: str = None, drive_id: str = None):
    """
    Retrieves the ID of a folder in Google Drive based on its path and optionally the shared drive ID.

    Args:
        service: The Google Drive API service instance.
        drive_path (str, optional): The path to the folder. Defaults to None.
        drive_id (str, optional): The ID of the shared drive. Defaults to None.

    Returns:
        str: The ID of the folder if found, None otherwise.

    Raises:
        FileNotFoundError: If the folder is not found within the specified Drive.
    """
    folder_id = None
    if drive_path:
        query = f"name='{drive_path}' and mimeType='application/vnd.google-apps.folder'"

        response = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                corpora="drive",
                driveId=drive_id,
            )
            .execute()
        )

        folders = response.get("files", [])
        if folders:
            folder_id = folders[0]["id"]
        else:
            raise FileNotFoundError(
                f"Folder '{drive_path}' not found in the specified drive."
            )
    return folder_id


def query_file_id(service, file_name, folder_id: str = None, drive_id: str = None):
    """
    Searches for a file by name in Google Drive and returns its ID.

    Args:
        service: The Google Drive API service instance.
        file_name (str): The name of the file to search for.
        folder_id (str, optional): The ID of the folder to search within. Defaults to None.
        drive_id (str, optional): The ID of the shared drive. Defaults to None.
    Returns:
        str: The ID of the file if found, None otherwise.
    """
    query = f"name='{file_name}' and trashed=false"
    if folder_id:
        query = query + f" and '{folder_id}' in parents"
    results = (
        service.files()
        .list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="drive",
            driveId=drive_id,
        )
        .execute()
    )
    items = results.get("files", [])

    if items:
        return items[0]["id"]  # Return the ID of the first match
    return None


def upload_to_drive(
    file_path: Path, shared_drive_name: str = None, drive_path: str = None
):
    """
    Uploads a file to a shared Google Drive or a regular Drive with folder specification.

    Args:
        file_path (Path): Path object of the local file to upload.
        shared_drive_name (str, optional): Name of the shared Google Drive. Defaults to None for regular Drive upload.
        drive_path (str, optional): Path of the folder to upload within the drive. If not exist it fails.


    Returns:
        str: The ID of the uploaded file in Google Drive.
    """
    service = setup_drive()

    drive_id = get_drive_id(shared_drive_name) if shared_drive_name else None
    folder_id = query_folder_id(service, drive_id=drive_id, drive_path=drive_path)
    file_id = query_file_id(
        service, file_path.name, folder_id=folder_id, drive_id=drive_id
    )

    file_metadata = {
        "name": file_path.name,
    }
    if drive_id:
        file_metadata["driveId"] = drive_id

    media = MediaFileUpload(str(file_path), resumable=True)

    if file_id:  # File exists, update it
        operation = service.files().update(
            fileId=file_id, body=file_metadata, media_body=media, supportsAllDrives=True
        )
    else:  # File doesn't exist, create it
        file_metadata["parents"] = [folder_id] if folder_id else []
        operation = service.files().create(
            body=file_metadata, media_body=media, fields="id", supportsAllDrives=True
        )

    file = operation.execute()

    return file.get("id")
