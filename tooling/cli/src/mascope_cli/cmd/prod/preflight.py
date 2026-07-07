"""
Preflight classification for `mascope prod update`.

Determines, without applying anything, whether updating the production stack
to a target release would (a) change any container image and (b) run a
database migration. The migration case is the only one that incurs a downtime
window, so classifying it up front is what lets an operator (or an automated
updater) schedule a maintenance window instead of guessing over the phone.

The source of truth mirrors the ``db_init`` service (``tooling/db-init.sh``):
the Alembic script head is baked into the backend image, and the applied
revision lives in the database's ``alembic_version`` table. A migration is
pending when the head baked into the target image is a revision the live
database has not yet reached.

All docker interaction goes through the small ``_run`` helper so tests can
stub it the same way ``test_prod_compose`` stubs ``lib.run``.
"""

import re
import subprocess
from dataclasses import dataclass
from typing import Optional


# Revision ids are the 12-char hex Alembic produces; the same pattern
# db-init.sh greps for out of `alembic heads`.
_REV_RE = re.compile(r"[a-f0-9]{12}")

# Paths inside the backend image, kept in sync with the Dockerfile and
# db-init.sh (the alembic tool location and the backend working directory
# that holds alembic.ini).
_ALEMBIC_BIN = "/opt/uv/tools/mascope/bin/alembic"
_BACKEND_WORKDIR = "/app/server/backend"

# Classification -> process exit code. Distinct non-zero codes let a shell
# updater branch on the outcome (`mascope prod update --check; case $? in ...`)
# without parsing output; --json is available for richer consumers.
CLASSIFICATIONS = {
    "up-to-date": 0,
    "fast-update": 10,
    "migration-update": 20,
}
ERROR_EXIT_CODE = 2


class PreflightError(RuntimeError):
    """Raised when the update cannot be classified (e.g. a failed image pull)."""


@dataclass
class UpdatePlan:
    """The outcome of classifying a pending update."""

    target: str
    classification: str
    image_changed: bool
    migration_pending: bool
    current_revision: Optional[str]
    target_revision: str

    @property
    def exit_code(self) -> int:
        """Process exit code for this classification."""
        return CLASSIFICATIONS[self.classification]

    def to_dict(self) -> dict:
        """JSON-serialisable view for `--json` output."""
        return {
            "target": self.target,
            "classification": self.classification,
            "image_changed": self.image_changed,
            "migration_pending": self.migration_pending,
            "current_revision": self.current_revision,
            "target_revision": self.target_revision,
        }


def _run(cmd: list[str], timeout: Optional[int] = 30) -> subprocess.CompletedProcess:
    """
    Run a docker command, capturing output. Never raises on non-zero exit —
    callers inspect ``returncode`` — but a timeout propagates as usual.
    """
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def pull_image(image: str) -> bool:
    """
    Pull an image into the local cache. Read-only with respect to running
    containers — it only downloads layers, pre-warming the cache for a
    subsequent `update`. Returns True on success.
    """
    # No timeout: image pulls are legitimately slow on a fresh release.
    return _run(["docker", "pull", image], timeout=None).returncode == 0


def image_alembic_head(image: str) -> Optional[str]:
    """
    Read the Alembic head revision baked into a backend image.

    Runs `alembic heads` in a throwaway container (entrypoint overridden, no
    DB connection required) exactly as db-init.sh does, and returns the first
    12-char revision id, or None if it could not be determined.
    """
    result = _run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "sh",
            image,
            "-c",
            f"cd {_BACKEND_WORKDIR} && {_ALEMBIC_BIN} heads",
        ]
    )
    if result.returncode != 0:
        return None
    match = _REV_RE.search(result.stdout)
    return match.group(0) if match else None


def db_current_revision(pg_container: str, db_user: str, db_name: str) -> Optional[str]:
    """
    Read the applied Alembic revision from the running Postgres container.

    Uses `docker exec` because the prod Postgres port is not published. Returns
    None when the revision cannot be read — a fresh database whose
    ``alembic_version`` table does not exist yet reads as None, which the
    classifier treats as "migration pending" (the first migration will run).
    """
    result = _run(
        [
            "docker",
            "exec",
            pg_container,
            "psql",
            "-U",
            db_user,
            "-d",
            db_name,
            "-tAc",
            "SELECT version_num FROM alembic_version LIMIT 1",
        ]
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _image_id(ref: str) -> Optional[str]:
    """Content id of a local image reference, or None if absent."""
    result = _run(["docker", "image", "inspect", "--format", "{{.Id}}", ref])
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _running_image_id(container: str) -> Optional[str]:
    """Content id of the image a running container was created from, or None."""
    result = _run(["docker", "inspect", "--format", "{{.Image}}", container])
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _image_changed(image: str, container: str) -> bool:
    """
    Whether deploying ``image`` would replace what ``container`` runs now.

    A missing running container (nothing to compare against) or a missing
    target image counts as changed, so the conservative answer is "yes, this
    would change something".
    """
    running = _running_image_id(container)
    target = _image_id(image)
    if running is None or target is None:
        return True
    return running != target


def classify(image_changed: bool, migration_pending: bool) -> str:
    """
    Map the two signals to a classification. A pending migration always wins:
    it means downtime and therefore a maintenance window, regardless of which
    images changed.
    """
    if migration_pending:
        return "migration-update"
    if image_changed:
        return "fast-update"
    return "up-to-date"


def build_plan(
    *,
    target: str,
    backend_image: str,
    backend_container: str,
    frontend_image: str,
    frontend_container: str,
    pg_container: str,
    db_user: str,
    db_name: str,
    pull: bool = True,
) -> UpdatePlan:
    """
    Classify the update to ``target`` without applying it.

    Pulls the target backend and frontend images (unless ``pull`` is False),
    reads the Alembic head baked into the backend image and the revision the
    live database has reached, and compares each running container's image
    against its pulled target.

    :raises PreflightError: if an image pull fails or the target migration head
        cannot be read — the same conditions under which an actual update
        would abort before touching the running stack.
    """
    if pull:
        for image in (backend_image, frontend_image):
            if not pull_image(image):
                raise PreflightError(f"Failed to pull image '{image}'")

    target_revision = image_alembic_head(backend_image)
    if target_revision is None:
        raise PreflightError(
            f"Could not read the Alembic head from image '{backend_image}'"
        )

    current_revision = db_current_revision(pg_container, db_user, db_name)
    migration_pending = current_revision != target_revision

    image_changed = _image_changed(backend_image, backend_container) or _image_changed(
        frontend_image, frontend_container
    )

    return UpdatePlan(
        target=target,
        classification=classify(image_changed, migration_pending),
        image_changed=image_changed,
        migration_pending=migration_pending,
        current_revision=current_revision,
        target_revision=target_revision,
    )
