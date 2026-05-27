"""Internal HTTP helpers for Mascope agents (file-agent, tof-agent).

These are low-level request wrappers used by agent services that upload
files to the Mascope backend. They are NOT part of the public SDK API.
New user-facing code should use :class:`MascopeClient` instead.
"""

import json
import os
import sys

import requests
import urllib3
from loguru import logger
from requests.exceptions import HTTPError, RequestException, Timeout


# Suppress InsecureRequestWarning from urllib3 (agents use verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Default service name sent in request headers.
# Agents override this at the package level: mascope_sdk.SERVICE_NAME = "file-agent"
SERVICE_NAME = "mascope_sdk"


def _get_service_name() -> str:
    """Return the current SERVICE_NAME from the package namespace."""
    pkg = sys.modules.get("mascope_sdk")
    if pkg is not None:
        return getattr(pkg, "SERVICE_NAME", SERVICE_NAME)
    return SERVICE_NAME


def api_post_file(
    url: str,
    path: str,
    access_token: str,
    filepath: str,
    upload_filename: str | None = None,
):
    """Send a POST request with a file upload.

    :param url: The base URL of the server.
    :param path: The API path to append to the base URL.
    :param access_token: Authorization token for API access.
    :param filepath: Path to the file to upload.
    :param upload_filename: Optional filename override for the uploaded file.
        If provided, the server will see this filename instead of the one on disk.
    :type upload_filename: str, optional
    :return: The response object on success, otherwise None.
    :rtype: requests.Response | None
    """
    full_url = url + "/api/" + path
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Service-Name": _get_service_name(),
        }
        with open(filepath, "rb") as file:
            if upload_filename:
                sanitized = os.path.basename(upload_filename)
                if sanitized != upload_filename:
                    raise ValueError(
                        f"upload_filename contains path components: {upload_filename!r}"
                    )
                files = [("files", (sanitized, file))]
            else:
                files = [("files", file)]
            resp = requests.post(
                full_url,
                files=files,
                headers=headers,
                verify=False,
                timeout=60,
            )
        resp.raise_for_status()
        message = json.loads(resp.content).get("message", None)
        if message is not None:
            logger.debug(message)
    except HTTPError as http_err:
        if resp.status_code in (401, 403):
            response = json.loads(resp.content)
            error_message = response.get("detail", {}).get("error_message", None)
            logger.error(f"{error_message} Please check your API token.")
        else:
            try:
                error_message = (
                    json.loads(resp.content)
                    .get("detail", {})
                    .get(
                        "error_message",
                        "No additional error information from the server.",
                    )
                )
            except json.JSONDecodeError:
                error_message = "Failed to decode error message from server response."
            logger.error(
                f"HTTP error: Unable to upload to {full_url}. "
                f"\nDetails: {http_err} \nServer message: {error_message}"
            )
        return None
    except Timeout:
        logger.error(f"Timeout error: The request to {full_url} timed out.")
        return None
    except RequestException as req_err:
        logger.error(
            f"Connection error: Could not connect to {full_url}. "
            f"Please check the URL and your network connection. \nDetails: {req_err}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Error: An unexpected error occurred while trying to reach {full_url}. "
            f"\nDetails: {str(e)}"
        )
        return None
    return resp
