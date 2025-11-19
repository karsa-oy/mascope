"""
Sample file record management module.

This module provides functions to interact with the sample file database
and filestore records via HTTP requests to the API service.
"""

from datetime import timedelta, datetime
import requests

from mascope_sdk import create_instrument_config
from mascope_backend.api.new.instrument_configs.schemas import PeakShape
from mascope_file.name import get_instrument_name

from .schema import SampleFileProps
from .runtime import runtime

HOST = runtime.config.server if runtime.mode == "prod" else "localhost"
URL = f"http://{HOST}:{runtime.meta.api_port}"


def create_sample_file_db_record(data: SampleFileProps, access_token: str) -> None:
    """Create a sample file database record via HTTP request.

    :param data: Sample file object to create
    :type data: SampleFileProps
    :param access_token: Access token required for request authentication
    :type access_token: str
    :raises Exception: HTTP request failed
    """
    runtime.logger.info(
        f"Creating sample file database record for file: {data.filename}"
    )

    utc_offset = timedelta(seconds=int(data.utc_offset))
    date = data.timestamp
    date_utc = (datetime.fromisoformat(date) - utc_offset).isoformat()

    sample_file_db_record = {
        "filename": data.filename,
        "instrument": get_instrument_name(data.filename),
        "datetime": date,
        "datetime_utc": date_utc,
        "length": data.length,
        "range": data.range,
        "method_file": data.method_file,
        "mz_calibration": data.mz_calibration,
        "polarity": data.polarity,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Service-Name": "file-converter",
        "Authorization": f"Bearer {access_token}",
    }

    try:
        response = requests.post(
            f"{URL}/api/sample/files",
            headers=headers,
            json=sample_file_db_record,
            timeout=180,
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
            f"{URL}/api/sample/files", headers=headers, params=params, timeout=10
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
            f"{URL}/api/sample/files/delete",
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


def create_instrument_config_db_record(
    sample_file_props: SampleFileProps,
    peakshape: PeakShape,
    resolution_function: list,
    access_token: str,
) -> None:
    """Create an instrument configuration database record via HTTP request.

    :param instrument_config: Instrument configuration object to create
    :type instrument_config: dict
    :param access_token: Access token required for request authentication
    :type access_token: str
    :raises Exception: HTTP request failed
    """
    runtime.logger.info(
        f"Creating instrument config database record for file: {sample_file_props.filename}"
    )

    create_instrument_config(
        mascope_url=URL,
        access_token=access_token,
        instrument=get_instrument_name(sample_file_props.filename),
        datetime_utc=sample_file_props.timestamp,
        peakshape=peakshape.model_dump(),
        resolution_function=resolution_function,
        method_file=sample_file_props.method_file,
    )
