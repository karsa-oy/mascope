"""
Rebuild path: ingest the bundle's raw files through the real upload pipeline.

Instead of dropping files into the file-converter's watch directory (which has
no auth/context and never registers a file context), this uploads each raw file
to the real ``/api/sample/files/upload`` endpoint - exactly what the File Agent
does. The endpoint registers the file context (auth) and writes the file to
``filestreams``, where the file-converter ingests it and runs the full
``RawProcessor`` -> peak detection -> matching pipeline.

Uploads are driven from a background thread because the app is launched in the
foreground; the thread waits for the backend HTTP server, then uploads.
"""

import threading
import time
from pathlib import Path

from mascope_cli.cmd.demo import bundles
from mascope_cli.cmd.demo._seed import DEMO_ENV  # noqa: F401 - re-exported convenience
from mascope_cli.runtime import runtime

# The fixed file-agent token + service name the demo seeds (mirror
# server seed_demo.DEMO_TOKENS["file-agent"]). Using the file-agent service
# replicates the File Agent's exact upload request.
_UPLOAD_TOKEN = "mascope_demo_file_agent_token"
_UPLOAD_SERVICE = "file-agent"
_UPLOAD_PATH = "sample/files/upload"


def _raw_dir(version: str | None, source_dir: "Path | None") -> Path:
    """Resolve the bundle's raw/ directory (published cache or local override)."""
    root = Path(source_dir) if source_dir else bundles.bundle_dir(version)
    src = root / "raw"
    if not src.is_dir():
        raise FileNotFoundError(f"No raw/ directory found at: {src}")
    return src


def _wait_for_backend(url: str, timeout: float = 300.0, poll: float = 2.0) -> bool:
    """
    Poll the backend until it serves HTTP (its OpenAPI schema returns 200).

    :param url: Backend base URL (e.g. ``http://localhost:8090``).
    :param timeout: Max seconds to wait.
    :param poll: Seconds between attempts.
    :return: ``True`` once ready, ``False`` on timeout.
    """
    import requests

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = requests.get(f"{url}/openapi.json", timeout=5)
            if resp.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(poll)
    return False


def upload_raw(version: str | None = None, source_dir: "Path | None" = None) -> int:
    """
    Upload the bundle's raw files to the real sample-file upload endpoint.

    Replicates the File Agent's request (bearer ``file-agent`` token +
    ``X-Service-Name: file-agent``) so the server registers context, stores the
    file, and the converter ingests it.

    :param version: Bundle version tag. Defaults to the registry default.
    :param source_dir: Local bundle directory override (see module docstring).
    :return: Number of files successfully uploaded.
    """
    import mascope_sdk
    from mascope_sdk import api_post_file

    src = _raw_dir(version, source_dir)
    url = f"http://localhost:{runtime.meta.api_port}"

    # Match the File Agent's service header for the upload request.
    mascope_sdk.SERVICE_NAME = _UPLOAD_SERVICE

    raw_files = sorted(p for p in src.iterdir() if p.suffix.lower() == ".raw")
    total = len(raw_files)
    runtime.logger.info(f"Uploading {total} raw file(s) to {url}/api/{_UPLOAD_PATH}")

    uploaded = 0
    for i, raw in enumerate(raw_files, 1):
        resp = api_post_file(
            url=url,
            path=_UPLOAD_PATH,
            access_token=_UPLOAD_TOKEN,
            filepath=str(raw),
        )
        if resp is not None:
            uploaded += 1
        if i % 25 == 0 or i == total:
            runtime.logger.info(f"  uploaded {uploaded}/{total}")

    if uploaded == total:
        runtime.logger.success(f"Uploaded all {total} raw file(s); ingestion proceeds")
    else:
        runtime.logger.warning(
            f"Uploaded {uploaded}/{total} raw file(s); {total - uploaded} failed "
            "(see errors above)"
        )
    return uploaded


def upload_raw_deferred(
    version: str | None = None, source_dir: "Path | None" = None
) -> None:
    """
    Upload raw files once the backend is serving, from a background daemon thread.

    The app is launched in the foreground, so this defers the uploads to a thread
    that first waits for the backend HTTP server to come up.

    :param version: Bundle version tag. Defaults to the registry default.
    :param source_dir: Local bundle directory override.
    """

    def _worker() -> None:
        url = f"http://localhost:{runtime.meta.api_port}"
        if not _wait_for_backend(url):
            runtime.logger.error(
                "Backend did not become ready in time; skipping raw upload. "
                "Once it is up, re-run 'mascope demo --rebuild' or upload manually."
            )
            return
        try:
            upload_raw(version, source_dir=source_dir)
        except Exception as e:  # noqa: BLE001 - background thread, just log
            runtime.logger.error(f"Deferred raw upload failed: {e}")

    threading.Thread(target=_worker, name="demo-upload-raw", daemon=True).start()
    runtime.logger.info(
        "Raw files will be uploaded to the server once the backend is ready; "
        "ingestion then proceeds in the background."
    )
