"""
Sample file record management module.

This module provides functions to interact with the sample file database
and filestore records via HTTP requests to the API service.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import requests

from mascope_backend.api.new.instrument_configs.lib import parse_instrument_functions
from mascope_backend.api.new.instrument_configs.schemas import PeakShape
from mascope_file.name import get_instrument_name

from .runtime import runtime
from .schema import SampleFileProps


HOST = runtime.config.server if runtime.mode == "prod" else "localhost"
URL = f"http://{HOST}:{runtime.meta.api_port}"


def fetch_instrument_functions(
    filename: str, access_token: str
) -> tuple[dict, callable]:
    """Fetch instrument functions for a sample file via HTTP and parse them.

    Calls "GET /api/instrument_configs/by_filename/{filename}" on the backend
    API and reconstructs the peakshape dict + resolution function callable.

    :param filename: Sample filename whose instrument config to fetch.
    :type filename: str
    :param access_token: Bearer token for request authentication.
    :type access_token: str
    :return: Tuple of (peakshape_dict, resolution_function_callable).
    :rtype: tuple[dict, callable]
    :raises ValueError: If the backend returns no instrument config.
    :raises Exception: If the HTTP request fails.
    """

    headers = {
        "X-Service-Name": "file-converter",
        "Authorization": f"Bearer {access_token}",
    }

    try:
        response = requests.get(
            f"{URL}/api/instrument_configs/by_filename/{filename}",
            headers=headers,
            timeout=30,
        )
        if response.status_code != 200:
            raise ValueError(
                f"Failed to fetch instrument config for {filename}: HTTP {response.status_code}"
            )

        data = response.json().get("data", {})
        # parse_instrument_functions expects a model with .peakshape and .resolution_function
        instrument_config = SimpleNamespace(
            peakshape=data["peakshape"],
            resolution_function=data["resolution_function"],
        )
        return parse_instrument_functions(instrument_config)

    except requests.exceptions.RequestException as e:
        raise Exception(
            f"Failed to fetch instrument functions for {filename}: {e}"
        ) from e


def create_sample_file_db_record(
    data: SampleFileProps, instrument_function_id: str, access_token: str
) -> None:
    """Create a sample file database record via HTTP request.

    :param data: Sample file object to create
    :type data: SampleFileProps
    :param instrument_function_id: FK to instrument config
    :type instrument_function_id: str
    :param access_token: Access token required for request authentication
    :type access_token: str
    :raises Exception: HTTP request failed
    """
    runtime.logger.info(
        f"Creating sample file database record for file: {data.filename}"
    )

    utc_offset = timedelta(seconds=int(data.utc_offset))
    date = data.timestamp
    date_utc = (
        (datetime.fromisoformat(date) - utc_offset)
        .replace(tzinfo=timezone.utc)
        .isoformat()
    )

    sample_file_db_record = {
        "instrument_function_id": instrument_function_id,
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


def is_blank_sample_file(filename: str, access_token: str) -> bool:
    """Return whether the sample file is a blank measurement (has no peaks).

    Blank files are persisted without an instrument_function_id.

    :param filename: Sample filename to inspect
    :type filename: str
    :param access_token: Access token for request authentication
    :type access_token: str
    :return: True if the sample file is blank, False otherwise
    :rtype: bool
    :raises Exception: If request fails unexpectedly or file is not found
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

        if response.status_code != 200:
            raise Exception(
                f"Failed to fetch sample file metadata for {filename}: HTTP {response.status_code}"
            )

        response_data = response.json()
        sample_files = response_data.get("data", [])
        if not sample_files:
            raise Exception(f"Sample file {filename} not found")

        sample_file = sample_files[0]
        return sample_file.get("instrument_function_id") is None

    except requests.exceptions.RequestException as e:
        runtime.logger.error(
            f"Failed to fetch sample file metadata for {filename}: {e}"
        )
        raise Exception(f"Failed to fetch sample file metadata: {e}") from e


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
) -> str:
    """Create an instrument configuration database record via HTTP request.

    :param instrument_config: Instrument configuration object to create
    :type instrument_config: dict
    :param access_token: Access token required for request authentication
    :type access_token: str
    :return: The created instrument_function_id
    :rtype: str
    :raises Exception: HTTP request failed
    """
    runtime.logger.info(
        f"Creating instrument config database record for file: {sample_file_props.filename}"
    )

    # Construct the request body based on the function parameters
    utc_offset = timedelta(seconds=int(sample_file_props.utc_offset))
    date = sample_file_props.timestamp
    date_utc = (
        (datetime.fromisoformat(date) - utc_offset)
        .replace(tzinfo=timezone.utc)
        .isoformat()
    )

    data = {
        "instrument": get_instrument_name(sample_file_props.filename),
        "datetime_utc": date_utc,
        "peakshape": peakshape.model_dump(),
        "resolution_function": resolution_function,
        "method_file": sample_file_props.method_file,
    }

    # Make the POST request to the instrument_configs endpoint
    headers = {
        "Content-Type": "application/json",
        "X-Service-Name": "file-converter",
        "Authorization": f"Bearer {access_token}",
    }

    try:
        response = requests.post(
            f"{URL}/api/instrument_configs",
            headers=headers,
            json=data,
            timeout=180,
        )

        if response.status_code != 201:
            raise Exception(
                f"Failed to create database record! Status code: {response.status_code}"
            )

        return (response.json())["data"]["instrument_function_id"]

    except requests.exceptions.RequestException as e:
        raise Exception(
            f"Failed to create database record due to request error: {e}"
        ) from e


def rematch_sample(
    sample_item_id: str, access_token: str, full_remove: bool = False, timeout: int = 30
) -> dict:
    """
    Trigger a rematch for a sample via the backend rematch route.

    :param sample_item_id: Sample item id to rematch
    :param access_token: Bearer token for authentication
    :param full_remove: If True, request a full removal before recompute
    :param timeout: HTTP request timeout in seconds
    :return: Response JSON from the backend (expected keys: 'message', 'process_id')
    :raises Exception: On network error or non-expected HTTP status
    """
    headers = {
        "X-Service-Name": "file-converter",
        "Authorization": f"Bearer {access_token}",
    }
    params = {"full_remove": "true" if full_remove else "false"}

    try:
        resp = requests.post(
            f"{URL}/api/match/rematch/sample/{sample_item_id}",
            headers=headers,
            params=params,
            timeout=timeout,
        )
        return resp.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to request rematch for {sample_item_id}: {e}") from e
