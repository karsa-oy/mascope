"""Internal HTTP helpers for Mascope agents (file-agent).

These are low-level request wrappers used by agent services that upload
files to the Mascope backend. They are NOT part of the public SDK API.
New user-facing code should use :class:`MascopeClient` instead.
"""

import base64
import json
import os
import sys
import time

import requests
import urllib3
from loguru import logger
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

from ._http import _is_retryable, _raise_for_status
from .exceptions import (
    AuthenticationError,
    MascopeAPIError,
    MascopeConnectionError,
    MascopeTimeoutError,
    NotFoundError,
    TusNotSupportedError,
)


# Suppress InsecureRequestWarning from urllib3 (agents use verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Default service name sent in request headers.
# Agents override this at the package level: mascope_sdk.SERVICE_NAME = "file-agent"
SERVICE_NAME = "mascope_sdk"

#: Path of the backend's TUS upload endpoint, relative to /api/.
TUS_UPLOAD_PATH = "sample/files/upload/tus"

#: Bytes sent per PATCH request. Each chunk is one HTTP request, so keep it
#: safely under reverse-proxy body limits (Cloudflare caps request bodies
#: at 100 MB) while staying large enough that overhead is negligible.
TUS_CHUNK_SIZE = 50 * 1024**2

#: Consecutive failed chunk attempts before the upload is abandoned.
TUS_MAX_ATTEMPTS = 4

#: Base for the exponential backoff between resumed chunk attempts
#: (2 s, 4 s, 8 s - matching the retry policy in ``_http``).
TUS_RETRY_BACKOFF_BASE = 2


def _get_service_name() -> str:
    """Return the current SERVICE_NAME from the package namespace."""
    pkg = sys.modules.get("mascope_sdk")
    if pkg is not None:
        return getattr(pkg, "SERVICE_NAME", SERVICE_NAME)
    return SERVICE_NAME


def _sanitize_upload_filename(upload_filename: str) -> str:
    """Validate that an upload filename carries no path components.

    :param upload_filename: The filename requested by the caller
    :type upload_filename: str
    :return: The validated filename
    :rtype: str
    :raises ValueError: if the name contains path components.
    """
    from pathlib import PurePosixPath, PureWindowsPath

    sanitized = PurePosixPath(PureWindowsPath(upload_filename).name).name
    if sanitized != upload_filename:
        raise ValueError(
            f"upload_filename contains path components: {upload_filename!r}"
        )
    return sanitized


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
            files = [("files", (_sanitize_upload_filename(upload_filename), file))]
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


def _tus_headers(access_token: str) -> dict:
    """Common headers for every TUS request."""
    return {
        "Authorization": f"Bearer {access_token}",
        "X-Service-Name": _get_service_name(),
        "Tus-Resumable": "1.0.0",
    }


def _tus_offset(upload_url: str, access_token: str) -> int | None:
    """Ask the server how many bytes of an upload it has (TUS HEAD).

    :param upload_url: Full URL of the upload resource
    :type upload_url: str
    :param access_token: Authorization token for API access
    :type access_token: str
    :return: The server-side offset, or None if it cannot be determined
    :rtype: int | None
    """
    try:
        resp = requests.head(
            upload_url,
            headers=_tus_headers(access_token),
            verify=False,
            timeout=30,
        )
    except RequestException:
        return None
    if resp.status_code != 200:
        return None
    try:
        return int(resp.headers["Upload-Offset"])
    except (KeyError, ValueError):
        return None


def api_post_file_tus(
    url: str,
    access_token: str,
    filepath: str,
    upload_filename: str | None = None,
    chunk_size: int = TUS_CHUNK_SIZE,
) -> None:
    """Upload a file with the resumable TUS protocol.

    Creates an upload resource on the backend's TUS endpoint and sends the
    file in ``chunk_size`` PATCH requests. A failed chunk is retried from
    the server-confirmed offset (TUS HEAD), so a network drop mid-file
    costs at most one chunk, not the whole upload - and no single request
    body ever exceeds ``chunk_size``, which keeps uploads of any size
    within reverse-proxy body limits. The backend processes the file when
    the last chunk arrives.

    :param url: The base URL of the server.
    :param access_token: Authorization token for API access.
    :param filepath: Path to the file to upload.
    :param upload_filename: Optional filename override for the uploaded file.
        If provided, the server will see this filename instead of the one on disk.
    :type upload_filename: str, optional
    :param chunk_size: Bytes per PATCH request.
    :type chunk_size: int, optional
    :raises ValueError: if ``upload_filename`` contains path components.
    :raises TusNotSupportedError: if the creation request is rejected with
        404/401, meaning the server has no token-accessible TUS endpoint
        (older Mascope release) - the caller's signal to fall back to the
        legacy upload endpoint.
    :raises MascopeTimeoutError: if a request times out (after retries).
    :raises MascopeConnectionError: if the server cannot be reached (after retries).
    :raises MascopeAPIError: on an error response; the concrete subclass
        (``AuthenticationError``, ``NotFoundError``, ``ValidationError``,
        ``ServerError``) and message carry the specific cause. Errors
        during chunk transfer keep these normal types and never signal
        fallback.
    """
    if upload_filename:
        filename = _sanitize_upload_filename(upload_filename)
    else:
        filename = os.path.basename(filepath)
    size = os.path.getsize(filepath)

    def b64(value: str) -> str:
        return base64.b64encode(value.encode("utf-8")).decode("ascii")

    # Create the upload resource. The server requires both filename and
    # filetype in the metadata; the type is not used for processing.
    create_url = f"{url}/api/{TUS_UPLOAD_PATH}/"
    create_headers = {
        **_tus_headers(access_token),
        "Upload-Length": str(size),
        "Upload-Metadata": (
            f"filename {b64(filename)},filetype {b64('application/octet-stream')}"
        ),
    }
    try:
        resp = requests.post(
            create_url, headers=create_headers, verify=False, timeout=60
        )
    except Timeout as e:
        raise MascopeTimeoutError(
            "The upload request timed out.", url=create_url
        ) from e
    except RequestException as e:
        raise MascopeConnectionError(
            "Could not connect to the server. Please check the URL "
            f"and your network connection ({e.__class__.__name__}).",
            url=create_url,
        ) from e
    try:
        _raise_for_status(resp, create_url)
    except (NotFoundError, AuthenticationError) as e:
        # Only the creation request may signal fallback: a 404 means no
        # TUS route, a 401 a route that is not token-accessible - both an
        # older Mascope release. The same statuses during chunk transfer
        # (e.g. the upload vanishing in a backend restart) keep their
        # normal types, so a transfer hiccup can never latch callers onto
        # the legacy path.
        raise TusNotSupportedError(
            e.message, status_code=e.status_code, url=create_url
        ) from e

    # The Location header's host/scheme depend on proxy headers; only its
    # upload id is trustworthy. Address the upload via our own base URL.
    location = resp.headers.get("Location", "")
    upload_id = location.rstrip("/").rsplit("/", 1)[-1]
    if not upload_id:
        raise MascopeAPIError(
            "The server did not return an upload location.", url=create_url
        )
    upload_url = f"{url}/api/{TUS_UPLOAD_PATH}/{upload_id}"

    if size == 0:
        return  # the server completes empty uploads at creation

    offset = 0
    failures = 0
    with open(filepath, "rb") as file:
        while offset < size:
            file.seek(offset)
            chunk = file.read(chunk_size)
            if not chunk:
                # The file shrank on disk mid-upload (e.g. rewritten by
                # the instrument); PATCHing empty bodies would loop
                # forever since the offset never advances.
                raise MascopeAPIError(
                    "The file changed on disk during the upload "
                    f"(expected {size} bytes, found only {offset}).",
                    url=upload_url,
                )
            try:
                resp = requests.patch(
                    upload_url,
                    data=chunk,
                    headers={
                        **_tus_headers(access_token),
                        "Upload-Offset": str(offset),
                        "Content-Type": "application/offset+octet-stream",
                    },
                    verify=False,
                    timeout=(10, 600),
                )
                _raise_for_status(resp, upload_url)
            except Exception as e:
                # Transient failures resume from the server-confirmed
                # offset: timeouts, dropped connections, retryable server
                # errors, and 409 (our offset disagrees with the server's,
                # e.g. a chunk partially arrived before a drop). Anything
                # else - rejected token, vanished upload, validation, or
                # a non-connection request error (SSL, proxy config) -
                # fails fast, matching the retry policy in _http.
                conflict = isinstance(e, MascopeAPIError) and e.status_code == 409
                transient = (
                    conflict
                    or isinstance(e, (Timeout, RequestsConnectionError))
                    or _is_retryable(e)
                )
                if not transient:
                    if isinstance(e, RequestException):
                        raise MascopeConnectionError(
                            f"The upload request failed: {e}", url=upload_url
                        ) from e
                    raise
                failures += 1
                if failures >= TUS_MAX_ATTEMPTS:
                    if isinstance(e, Timeout):
                        raise MascopeTimeoutError(
                            "The upload timed out.", url=upload_url
                        ) from e
                    if isinstance(e, RequestsConnectionError):
                        raise MascopeConnectionError(
                            "Lost the connection while uploading "
                            f"({e.__class__.__name__}).",
                            url=upload_url,
                        ) from e
                    raise
                delay = TUS_RETRY_BACKOFF_BASE**failures
                logger.info(
                    "Chunk upload failed (attempt {}/{}), resuming in {}s: {}",
                    failures,
                    TUS_MAX_ATTEMPTS,
                    delay,
                    e,
                )
                time.sleep(delay)
                server_offset = _tus_offset(upload_url, access_token)
                if server_offset is not None:
                    offset = server_offset
                continue
            failures = 0
            offset += len(chunk)

    logger.debug(f"TUS upload of {filename} completed ({size} bytes)")
