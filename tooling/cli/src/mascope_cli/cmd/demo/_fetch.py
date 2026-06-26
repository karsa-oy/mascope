"""
Download and verify a published demo bundle into the local cache.

Pure download/extract/verify logic - no Typer concerns. The CLI command in
``main.py`` wraps these helpers with user-facing messaging.
"""

import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from mascope_cli.cmd.demo import bundles
from mascope_cli.runtime import runtime


def _extract_archive(archive: Path, dest: Path) -> None:
    """
    Extract a ``.zip`` or ``.tar.gz`` archive into ``dest``.

    The archive is expected to contain the bundle contents at its top level
    (``manifest.json``, ``raw/``, ``snapshot/`` ...). If it instead wraps them in
    a single top-level directory, that directory's contents are flattened into
    ``dest`` so the layout is consistent regardless of how it was packed.

    :param archive: Path to the downloaded archive.
    :param dest: Target bundle directory (created/overwritten by the caller).
    :raises ValueError: If the archive format is unsupported.
    """
    staging = dest.parent / f"{dest.name}.staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(staging)
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive) as tf:
            tf.extractall(staging)
    else:
        shutil.rmtree(staging, ignore_errors=True)
        raise ValueError(f"Unsupported archive format: {archive.name}")

    # Flatten a single wrapping directory if present.
    entries = list(staging.iterdir())
    root = entries[0] if len(entries) == 1 and entries[0].is_dir() else staging

    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(root), str(dest))
    shutil.rmtree(staging, ignore_errors=True)


def _download(url: str, dest: Path) -> None:
    """
    Stream a URL to a local file, logging coarse progress.

    :param url: Source URL.
    :param dest: Destination file path (parent created automatically).
    :raises OSError: On network/IO failure (propagated from urllib).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    runtime.logger.info(f"Downloading {url}")

    with urllib.request.urlopen(url) as response:  # noqa: S310 - trusted Zenodo URL
        total = int(response.headers.get("Content-Length", 0))
        read = 0
        next_mark = 10
        with dest.open("wb") as out:
            for chunk in iter(lambda: response.read(1 << 20), b""):
                out.write(chunk)
                read += len(chunk)
                if total:
                    pct = read * 100 // total
                    if pct >= next_mark:
                        runtime.logger.info(f"  ...{pct}%")
                        next_mark = pct - (pct % 10) + 10


def fetch(version: str | None = None, force: bool = False) -> Path:
    """
    Ensure a demo bundle is present and verified in the local cache.

    If already cached and intact, returns immediately unless ``force`` is set.
    Otherwise downloads the archive from the registered URL, extracts it, and
    verifies every file against the manifest checksums.

    :param version: Bundle version tag. Defaults to the registry default.
    :param force: Re-download even if a valid cached copy exists.
    :raises RuntimeError: If the bundle has no published URL, the download
                          fails, or checksum verification fails.
    :return: Path to the verified bundle directory.
    """
    bundle = bundles.get_bundle(version)
    dest = bundles.bundle_dir(version)

    if bundles.is_cached(version) and not force:
        problems = bundles.verify_manifest(version)
        if not problems:
            runtime.logger.success(f"Demo bundle '{bundle.version}' already cached")
            return dest
        runtime.logger.warning(
            f"Cached bundle '{bundle.version}' failed verification; re-fetching"
        )

    if not bundle.url:
        raise RuntimeError(
            f"Demo bundle '{bundle.version}' has no published download URL yet. "
            "Build one locally with 'mascope demo snapshot', or set its URL in "
            "tooling/cli/src/mascope_cli/cmd/demo/bundles.py once published."
        )

    archive = bundles.cache_root() / f"{bundle.version}{_suffix(bundle.url)}"
    _download(bundle.url, archive)

    if bundle.archive_sha256:
        actual = bundles.sha256_file(archive)
        # Case-insensitive: hashlib emits lowercase, but a hash pasted into the
        # registry from e.g. PowerShell's Get-FileHash is uppercase.
        if actual.lower() != bundle.archive_sha256.lower():
            raise RuntimeError(
                f"Archive checksum mismatch for '{bundle.version}': "
                f"expected {bundle.archive_sha256[:12]}..., got {actual[:12]}..."
            )

    runtime.logger.info("Extracting bundle...")
    _extract_archive(archive, dest)
    archive.unlink(missing_ok=True)

    problems = bundles.verify_manifest(version)
    if problems:
        raise RuntimeError(
            "Bundle verification failed after download:\n  - " + "\n  - ".join(problems)
        )

    runtime.logger.success(f"Demo bundle '{bundle.version}' fetched and verified")
    return dest


def _suffix(url: str) -> str:
    """Return the archive suffix (``.zip`` or ``.tar.gz``) implied by a URL."""
    lowered = url.lower()
    if lowered.endswith(".tar.gz") or lowered.endswith(".tgz"):
        return ".tar.gz"
    return ".zip"
