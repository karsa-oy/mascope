"""
Automated update orchestration for `mascope prod update --auto`.

Runs unattended (e.g. from a systemd timer). It resolves the newest pinned
release, classifies it with the preflight, and acts by classification:

- up-to-date: nothing to do.
- fast update (new images, no migration): apply it inside the maintenance
  window, guarded by a post-apply health check. On failure it alerts and
  stops - it never rolls back automatically (an operator decides).
- migration update (downtime): do NOT apply unattended. Record it as a pending
  update and notify, so a human can schedule the window. Applying migration
  updates on confirmation or after a grace period is handled separately.

Finding the latest release and downloading its manifest use the public GitHub
REST API over plain HTTPS - no token and no ``gh`` needed, since the repository
and its release assets are public. A nightly timer stays well within the
anonymous rate limit. Both calls go through small seams that tests stub.
"""

import datetime
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from mascope_cli.cmd.prod.release_manifest import MANIFEST_FILENAME


# Exit codes for the --auto run, chosen so a timer/monitor can distinguish
# "handled" from "needs a human" from "broken" without parsing output.
AUTO_OK = 0  # nothing to do, or a fast update applied cleanly
AUTO_MIGRATION_PENDING = 30  # a migration update was recorded + notified
AUTO_ERROR = 2  # discovery, apply, or health check failed


@dataclass
class PendingUpdate:
    """A migration update seen but not yet applied."""

    version: str
    alembic_head: str
    first_seen_at: str
    # Postpone auto-apply until this local ISO timestamp (set by a snooze).
    snooze_until: Optional[str] = None
    # Operator/customer confirmed: apply at the next window without waiting out
    # the grace period.
    confirmed: bool = False

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "alembic_head": self.alembic_head,
            "first_seen_at": self.first_seen_at,
            "snooze_until": self.snooze_until,
            "confirmed": self.confirmed,
        }


def _now() -> datetime.datetime:
    """Current local time (seam for tests)."""
    return datetime.datetime.now()


def update_dir(mascope_path: str) -> Path:
    """Directory holding the updater's state and status log."""
    return Path(mascope_path) / ".runtime" / "update"


# --- Maintenance window ---


def parse_window(spec: Optional[str]) -> Optional[tuple[int, int]]:
    """
    Parse a ``"HH-HH"`` local-hour maintenance window (e.g. ``"2-5"``).

    Returns None when ``spec`` is empty (meaning "no restriction - any time").

    :raises ValueError: if the spec is malformed or hours are out of range.
    """
    if not spec:
        return None
    try:
        start_s, end_s = spec.split("-", 1)
        start, end = int(start_s), int(end_s)
    except ValueError:
        raise ValueError(f"Invalid window '{spec}' - expected 'HH-HH' (e.g. '2-5')")
    for h in (start, end):
        if not 0 <= h <= 23:
            raise ValueError(f"Window hour {h} out of range 0-23")
    return start, end


def in_window(now: datetime.datetime, window: Optional[tuple[int, int]]) -> bool:
    """
    Whether ``now`` falls in the window. A window that wraps midnight
    (start > end, e.g. 22-3) is handled. None means always allowed.
    """
    if window is None:
        return True
    start, end = window
    hour = now.hour
    if start <= end:
        return start <= hour < end
    # Wraps midnight: in-window if at/after start OR before end.
    return hour >= start or hour < end


# --- Pending-update state ---


def load_pending(mascope_path: str) -> Optional[PendingUpdate]:
    """Load the recorded pending update, or None if there is none."""
    path = update_dir(mascope_path) / "state.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8")).get("pending")
    except (OSError, json.JSONDecodeError):
        return None
    if not data:
        return None
    return PendingUpdate(
        version=data["version"],
        alembic_head=data["alembic_head"],
        first_seen_at=data["first_seen_at"],
        snooze_until=data.get("snooze_until"),
        confirmed=data.get("confirmed", False),
    )


def save_pending(mascope_path: str, pending: PendingUpdate) -> None:
    """Persist the pending update, creating the update dir if needed."""
    d = update_dir(mascope_path)
    d.mkdir(parents=True, exist_ok=True)
    (d / "state.json").write_text(
        json.dumps({"pending": pending.to_dict()}, indent=2) + "\n", encoding="utf-8"
    )


def clear_pending(mascope_path: str) -> None:
    """Remove any recorded pending update."""
    path = update_dir(mascope_path) / "state.json"
    if path.exists():
        path.unlink()


def record_pending(mascope_path: str, version: str, alembic_head: str) -> PendingUpdate:
    """
    Record ``version`` as pending, preserving ``first_seen_at`` if the same
    version was already pending (so the grace clock is not reset each tick).
    """
    existing = load_pending(mascope_path)
    if existing is not None and existing.version == version:
        return existing
    pending = PendingUpdate(
        version=version,
        alembic_head=alembic_head,
        first_seen_at=_now().replace(microsecond=0).isoformat(),
    )
    save_pending(mascope_path, pending)
    return pending


def snooze_pending(mascope_path: str, days: int) -> Optional[PendingUpdate]:
    """
    Postpone auto-apply of the pending update by ``days``. Returns the updated
    record, or None if there is nothing pending.
    """
    pending = load_pending(mascope_path)
    if pending is None:
        return None
    pending.snooze_until = (
        (_now() + datetime.timedelta(days=days)).replace(microsecond=0).isoformat()
    )
    # Snoozing overrides a prior confirmation - the operator changed their mind.
    pending.confirmed = False
    save_pending(mascope_path, pending)
    return pending


def confirm_pending(mascope_path: str) -> Optional[PendingUpdate]:
    """
    Mark the pending update confirmed so it applies at the next window without
    waiting out the grace period. Returns the updated record, or None if there
    is nothing pending.
    """
    pending = load_pending(mascope_path)
    if pending is None:
        return None
    pending.confirmed = True
    pending.snooze_until = None
    save_pending(mascope_path, pending)
    return pending


def should_apply_migration(
    pending: PendingUpdate,
    now: datetime.datetime,
    grace_days: int,
    window: Optional[tuple[int, int]],
) -> bool:
    """
    Decide whether a pending migration update may be applied unattended now.

    True only when inside the maintenance window and not snoozed, and either
    the operator confirmed it or its grace period has elapsed since it was
    first seen.
    """
    if not in_window(now, window):
        return False
    if pending.snooze_until and now < datetime.datetime.fromisoformat(
        pending.snooze_until
    ):
        return False
    if pending.confirmed:
        return True
    grace_deadline = datetime.datetime.fromisoformat(
        pending.first_seen_at
    ) + datetime.timedelta(days=grace_days)
    return now >= grace_deadline


def record_status(mascope_path: str, message: str) -> None:
    """Append a timestamped line to the updater's status log."""
    d = update_dir(mascope_path)
    d.mkdir(parents=True, exist_ok=True)
    stamp = _now().replace(microsecond=0).isoformat()
    with (d / "status.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {message}\n")


# --- docker command runner (used by the health check) ---


def _run(cmd: list[str], timeout: Optional[int] = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, check=False, timeout=timeout
    )


# --- GitHub release discovery (public, tokenless HTTPS) ---

_GITHUB_API = "https://api.github.com"
# GitHub rejects API requests that send no User-Agent.
_HTTP_HEADERS = {"User-Agent": "mascope-cli", "Accept": "application/vnd.github+json"}


def _http_get_json(url: str, timeout: int = 30) -> dict:
    """GET ``url`` and parse the JSON body. Raises on transport/parse errors."""
    request = urllib.request.Request(url, headers=_HTTP_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _http_download(url: str, dest: Path, timeout: int = 30) -> None:
    """Download ``url`` to ``dest``. Raises on transport errors."""
    request = urllib.request.Request(url, headers=_HTTP_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        with dest.open("wb") as fh:
            shutil.copyfileobj(response, fh)


def latest_release_tag(repo: str) -> Optional[str]:
    """
    Newest published release tag for ``repo`` (e.g. ``v1.4.0``), read from the
    public GitHub REST API without authentication.

    Returns None if it cannot be determined (no releases, no network).
    """
    try:
        data = _http_get_json(f"{_GITHUB_API}/repos/{repo}/releases/latest")
    except (urllib.error.URLError, OSError, ValueError):
        return None
    tag = data.get("tag_name")
    return tag or None


def download_manifest(repo: str, tag: str, dest_dir: Path) -> Optional[Path]:
    """
    Download the release's manifest asset into ``dest_dir``. Returns the path,
    or None if the release has no manifest asset (releases predating the
    manifest) or it could not be fetched.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        release = _http_get_json(f"{_GITHUB_API}/repos/{repo}/releases/tags/{tag}")
    except (urllib.error.URLError, OSError, ValueError):
        return None

    asset_url = next(
        (
            asset.get("browser_download_url")
            for asset in release.get("assets", [])
            if asset.get("name") == MANIFEST_FILENAME
        ),
        None,
    )
    if not asset_url:
        return None

    path = dest_dir / MANIFEST_FILENAME
    try:
        _http_download(asset_url, path)
    except (urllib.error.URLError, OSError):
        return None
    return path if path.exists() else None


# --- Health check ---


def health_status(container: str) -> Optional[str]:
    """Docker health status of a container (healthy/starting/unhealthy), or None."""
    result = _run(
        ["docker", "inspect", "--format", "{{.State.Health.Status}}", container]
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def wait_healthy(container: str, timeout: int = 180, interval: int = 5) -> bool:
    """
    Poll ``container`` until it reports healthy or ``timeout`` seconds elapse.

    A container without a healthcheck (status None) is treated as not-healthy
    here; callers point this at the backend, which defines one.
    """
    deadline = _now() + datetime.timedelta(seconds=timeout)
    while _now() < deadline:
        if health_status(container) == "healthy":
            return True
        _sleep(interval)
    return health_status(container) == "healthy"


def _sleep(seconds: int) -> None:
    """Sleep seam (overridden in tests to avoid real waits)."""
    import time

    time.sleep(seconds)
