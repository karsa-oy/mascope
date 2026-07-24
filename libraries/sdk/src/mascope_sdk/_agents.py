"""Internal HTTP helpers for Mascope agents (file-agent).

These are low-level request wrappers used by agent services that upload
files to the Mascope backend. They are NOT part of the public SDK API.
New user-facing code should use :class:`MascopeClient` instead.
"""

import json
import sys

import requests
import urllib3
from loguru import logger
from requests.exceptions import RequestException, Timeout

from ._http import _raise_for_status
from .exceptions import MascopeConnectionError, MascopeTimeoutError


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
) -> requests.Response:
    """Send a POST request with a file upload.

    :param url: The base URL of the server.
    :param path: The API path to append to the base URL.
    :param access_token: Authorization token for API access.
    :param filepath: Path to the file to upload.
    :param upload_filename: Optional filename override for the uploaded file.
        If provided, the server will see this filename instead of the one on disk.
    :type upload_filename: str, optional
    :return: The response object on success.
    :rtype: requests.Response
    :raises ValueError: if ``upload_filename`` contains path components.
    :raises MascopeTimeoutError: if the request times out.
    :raises MascopeConnectionError: if the server cannot be reached.
    :raises MascopeAPIError: on an error response; the concrete subclass
        (``AuthenticationError``, ``NotFoundError``, ``ValidationError``,
        ``ServerError``) and message carry the specific cause so callers can
        act on it (e.g. not retry on a rejected token).
    """
    full_url = url + "/api/" + path
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Service-Name": _get_service_name(),
    }
    with open(filepath, "rb") as file:
        if upload_filename:
            from pathlib import PurePosixPath, PureWindowsPath

            sanitized = PurePosixPath(PureWindowsPath(upload_filename).name).name
            if sanitized != upload_filename:
                raise ValueError(
                    f"upload_filename contains path components: {upload_filename!r}"
                )
            files = [("files", (sanitized, file))]
        else:
            files = [("files", file)]
        try:
            resp = requests.post(
                full_url,
                files=files,
                headers=headers,
                verify=False,
                timeout=60,
            )
        except Timeout as e:
            raise MascopeTimeoutError(
                "The upload request timed out.", url=full_url
            ) from e
        except RequestException as e:
            raise MascopeConnectionError(
                "Could not connect to the server. Please check the URL "
                f"and your network connection ({e.__class__.__name__}).",
                url=full_url,
            ) from e

    # Raises a typed MascopeAPIError subclass carrying the server's message.
    _raise_for_status(resp, full_url)

    try:
        message = json.loads(resp.content).get("message", None)
    except (json.JSONDecodeError, AttributeError):
        message = None
    if message is not None:
        logger.debug(message)
    return resp
