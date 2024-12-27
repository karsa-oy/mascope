from datetime import timedelta, datetime
import requests
from mascope_lib.file_func import get_instrument_type
from mascope_lib.util import timestamp_from_filename
from mascope_runtime import MascopeRuntimeModule

runtime = MascopeRuntimeModule("file-converter")

host = runtime.config.server if runtime.mode == "prod" else "localhost"
url = f"http://{host}:{runtime.meta.api_port}"


def create_sample_file_db_record(data):
    """Create a sample file database record by a HTTP request

    :param data: Sample file object to create
    :type data: dict
    :raises Exception: HTTP request failed
    """
    filename = data["filename"]
    instrument_type = get_instrument_type(filename)
    runtime.logger.info(f"Creating sample file record for file: {filename}")
    instrument_name = filename.split("_")[0]
    committed_length = data["committed_length"]
    utc_offset = timedelta(seconds=int(data["utc_offset"]))
    mz_calibration = data.get("mz_calibration")
    polarity = data.get("polarity")
    method_file = data.get("method_file")
    tic = data.get("tic")

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
        "tic": tic,
        "polarity": polarity,
    }
    if method_file:
        sample_file_db_record["method_file"] = method_file

    headers = {"Content-Type": "application/json"}

    response = requests.post(
        f"{url}/api/sample/files", headers=headers, json=sample_file_db_record
    )
    if response.status_code != 201:
        raise Exception(
            f"Failed to create database record! Status code: {response.status_code}"
        )
