"""
Detect when the installed ``mascope`` CLI has drifted behind the checkout.

``mascope prod update`` refreshes the Docker images but never the CLI binary
itself. In a production deploy the ``mascope`` command is a uv tool installed
from the source checkout (``tooling/ubuntu.sh``); the operator later moves the
checkout forward (``git pull`` / checking out a new release) and runs
``prod update``, which pulls the new images but leaves the tool running the
code it was last installed from. A command that only exists in the newer
checkout (e.g. the ``prod doctor`` added in v1.4.x) is then invisible until
someone reinstalls the tool - which bit production once already.

This module compares the Python source the running CLI imports against the
checkout's ``tooling/cli/src/mascope_cli`` tree and, when they differ, lets the
update command surface the exact reinstall command. It never replaces the
running binary itself: the update may be running *from* the stale tool, so an
in-place self-reinstall mid-run is risky (see ``main`` for the rationale).

The comparison is a content hash of the ``*.py`` files (package-relative path +
bytes), so it catches added, removed, renamed, or edited modules regardless of
whether the CLI package version was bumped. That matters: the drift that bit
prod was a new command added without a version bump, which a version-string
comparison would have missed entirely.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# The checkout's CLI source, relative to the repo root (MASCOPE_PATH points at
# the checkout root in a prod deploy - see tooling/ubuntu.sh set_envvar).
_CLI_SRC_RELPATH = ("tooling", "cli", "src", "mascope_cli")


@dataclass
class DriftResult:
    """Outcome of comparing the installed CLI against the checkout source."""

    drifted: bool
    # Human-readable one-liner describing the outcome (for logs).
    reason: str
    # The exact command to rebuild + reinstall the tool, set only when drifted.
    reinstall: Optional[str] = None


def installed_package_dir() -> Path:
    """Directory of the ``mascope_cli`` package the running CLI imports from."""
    import mascope_cli

    return Path(mascope_cli.__file__).resolve().parent


def checkout_package_dir(mascope_path: str) -> Path:
    """Where the checkout's ``mascope_cli`` source lives under MASCOPE_PATH."""
    return Path(mascope_path, *_CLI_SRC_RELPATH)


def reinstall_command(mascope_path: str) -> str:
    """
    The exact command that rebuilds and reinstalls the CLI from the checkout.

    Mirrors the ``uv tool install`` invocation in ``tooling/ubuntu.sh``
    (install_mascope) so an operator can copy-paste it: force a rebuild from
    source (the workspace cannot tell placeholder-versioned builds apart),
    pin Python 3.12, and link the ``mascope`` entry point from the mascope-cli
    member. Keep in sync with ubuntu.sh if that command changes.
    """
    return (
        f'cd "{mascope_path}" && CFLAGS="-std=c17" '
        "uv tool install --force --reinstall --python 3.12 . "
        "--with-executables-from mascope-cli"
    )


def _tree_hash(package_dir: Path) -> Optional[str]:
    """
    Content hash of every ``*.py`` file under ``package_dir``.

    Folds each file's package-relative POSIX path and bytes into one digest so
    an added, removed, renamed, or edited module changes it. Byte-compiled
    caches never match ``*.py``, so ``__pycache__`` is ignored automatically.
    Returns None when the tree has no Python files (nothing to compare).
    """
    files = sorted(package_dir.rglob("*.py"))
    if not files:
        return None
    digest = hashlib.sha256()
    for path in files:
        rel = path.relative_to(package_dir).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def detect(mascope_path: str) -> Optional[DriftResult]:
    """
    Compare the installed CLI's Python source with the checkout's.

    :return: None when the check does not apply - there is no CLI source under
             ``mascope_path`` (an operator wheel-only install pointed at a
             runtime home rather than a checkout, where drift is impossible), or
             the CLI already imports straight from that checkout (an editable /
             source run, e.g. in development, which can never be stale).
             Otherwise a :class:`DriftResult` reporting whether the installed
             tree differs from the checkout.
    :rtype: DriftResult | None
    """
    checkout = checkout_package_dir(mascope_path)
    if not checkout.is_dir():
        return None  # no source checkout to drift from

    installed = installed_package_dir()
    if installed.resolve() == checkout.resolve():
        return None  # running straight from the checkout - cannot be stale

    checkout_hash = _tree_hash(checkout)
    installed_hash = _tree_hash(installed)
    if checkout_hash is None or installed_hash is None:
        return None  # nothing to compare

    if installed_hash == checkout_hash:
        return DriftResult(drifted=False, reason="installed CLI matches the checkout")

    return DriftResult(
        drifted=True,
        reason=(
            "installed 'mascope' CLI is out of sync with the checkout at "
            f"{mascope_path}"
        ),
        reinstall=reinstall_command(mascope_path),
    )
