"""
Sample file record management module.

This module provides functions to interact with the sample file database
and filestore records via HTTP requests to the API service.
"""

from datetime import timedelta, datetime
import requests

from mascope_file.name import get_instrument_type, timestamp_from_filename
from mascope_runtime import Runtime

runtime = Runtime("file-converter")

host = runtime.config.server if runtime.mode == "prod" else "localhost"
url = f"http://{host}:{runtime.meta.api_port}"


def create_sample_file_db_record(data: dict, access_token: str) -> None:
    """Create a sample file database record via HTTP request.

    :param data: Sample file object to create
    :type data: dict
    :param access_token: Access token required for request authentication
    :type access_token: str
    :raises Exception: HTTP request failed
    """
    filename = data["filename"]
    instrument_type = get_instrument_type(filename)
    runtime.logger.info(f"Creating sample file database record for file: {filename}")

    instrument_name = filename.split("_")[0]
    committed_length = data["committed_length"]
    utc_offset = timedelta(seconds=int(data["utc_offset"]))
    mz_calibration = data.get("mz_calibration")
    method_file = data.get("method_file")

    if instrument_type == "tof":
        date = timestamp_from_filename(filename).isoformat()
    else:
        date = data.get("timestamp")

    date_utc = (datetime.fromisoformat(date) - utc_offset).isoformat()

    sample_file_db_record = {
        "filename": filename,
        "instrument": instrument_name,
        "datetime": date,
        "datetime_utc": date_utc,
        "length": committed_length,
        "range": data["range"],
        "mz_calibration": mz_calibration,
        "polarity": data["polarity"],
    }

    if method_file:
        sample_file_db_record["method_file"] = method_file

    headers = {
        "Content-Type": "application/json",
        "X-Service-Name": "file-converter",
        "Authorization": f"Bearer {access_token}",
    }

    try:
        response = requests.post(
            f"{url}/api/sample/files",
            headers=headers,
            json=sample_file_db_record,
            timeout=30,
        )

        if response.status_code != 201:
            raise Exception(
                f"Failed to create database record! Status code: {response.status_code}"
            )

    except requests.exceptions.RequestException as e:
        raise Exception(
            f"Failed to create database record due to request error: {e}"
        ) from e


def check_sample_file_db_record(filename: str, access_token: str) -> bool:
    """Check if a sample file database record exists by filename.

    :param filename: Sample filename to check
    :type filename: str
    :param access_token: Access token for request authentication
    :type access_token: str
    :return: True if record exists, False otherwise
    :rtype: bool
    :raises Exception: If request fails unexpectedly
    """
    headers = {
        "X-Service-Name": "file-converter",
        "Authorization": f"Bearer {access_token}",
    }

    params = {"filename": filename, "limit": 1}

    try:
        response = requests.get(
            f"{url}/api/sample/files", headers=headers, params=params, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("results") == 1
        else:
            runtime.logger.warning(
                f"Failed to check sample file record for {filename}: HTTP {response.status_code}"
            )
            return False

    except requests.exceptions.RequestException as e:
        runtime.logger.error(
            f"Failed to check sample file existence for {filename}: {e}"
        )
        raise Exception(f"Failed to check sample file record: {e}") from e


def delete_sample_file_by_filename(filename: str, access_token: str) -> bool:
    """Delete sample file from filestore by filename via HTTP request.

    :param filename: Sample filename to delete from filestore
    :type filename: str
    :param access_token: Access token for request authentication
    :type access_token: str
    :return: True if deletion was successful, False if file not found
    :rtype: bool
    :raises Exception: If request fails unexpectedly
    """
    headers = {
        "X-Service-Name": "file-converter",
        "Authorization": f"Bearer {access_token}",
    }

    try:
        response = requests.post(
            f"{url}/api/sample/files/delete",
            headers=headers,
            json={"filenames": [filename]},
            timeout=30,
        )

        if response.status_code in [200, 207]:
            runtime.logger.debug(f"Successfully deleted file: {filename}")
            return True
        elif response.status_code == 422:
            runtime.logger.debug(f"File not found for deletion: {filename}")
            return False
        else:
            runtime.logger.error(
                f"Failed to delete file {filename}: HTTP {response.status_code}"
            )
            raise Exception(f"Failed to delete file: HTTP {response.status_code}")

    except requests.exceptions.RequestException as e:
        runtime.logger.error(f"Failed to delete file {filename}: {e}")
        raise Exception(f"Failed to delete file: {e}") from e
