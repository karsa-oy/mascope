"""
Shared test utilities for the Mascope test suite.

Provides:
- ID generation (`gen_test_id`)
- Test database connection parameters (`TEST_DB_HOST` / `_PORT` / `_USER`)
  and password resolution (`get_test_password`)

The connection helpers are used by both the root conftest (async engine
factory) and the migrations test conftest (sync engine for stairway).
Centralised here so test infrastructure shares a single source of truth
for connection parameters.
"""

import os
from pathlib import Path

from mascope_backend.db.id import gen_id


# --- Test database connection parameters ---

# Resolved at import time from TEST_DB_* env vars (CI override) with dev
# container defaults as fallback. Intentionally independent of
# runtime.config.database so test infrastructure stays hermetic — tests
# must not be affected by whichever Mascope env happens to be active.
TEST_DB_HOST: str = os.environ.get("TEST_DB_HOST", "localhost")
TEST_DB_PORT: str = os.environ.get("TEST_DB_PORT", "5432")
TEST_DB_USER: str = os.environ.get("TEST_DB_USER", "mascope_user")

# --- Credential resolution ---


def get_test_password() -> str:
    """Resolve PostgreSQL password for test connections.

    Resolution order:
    - `POSTGRES_TEST_PASSWORD` env var (CI and explicit local override)
    - `${MASCOPE_PATH}/.runtime/secrets/postgres_password.txt` (local dev)

    :return: PostgreSQL password string
    :rtype: str
    :raises RuntimeError: If neither source is available
    """
    password = os.environ.get("POSTGRES_TEST_PASSWORD")
    if password:
        return password

    mascope_path = os.environ.get("MASCOPE_PATH")
    if not mascope_path:
        raise RuntimeError(
            "Cannot resolve test DB password: "
            "set POSTGRES_TEST_PASSWORD or MASCOPE_PATH env var"
        )
    secret_path = Path(mascope_path) / ".runtime" / "secrets" / "postgres_password.txt"
    if not secret_path.exists():
        raise RuntimeError(
            f"Cannot resolve test DB password: secret file not found at {secret_path}"
        )
    return secret_path.read_text().strip()


# --- ID generation ---


def gen_test_id(size: int = 16) -> str:
    """Generate a random ID of exactly `size` characters.

    Delegates to `mascope_backend.db.id.gen_id` — same alphabet and
    generation logic used by application models (alphanumeric only, no
    `-` or `_`). Centralised here so test files have a single import
    point and any test-specific ID generation changes stay in one place.

    The default size of 16 matches the `VARCHAR(16)` constraint on
    primary key columns — pass `size` explicitly when a column has a
    different constraint.

    :param size: Character length of the generated ID
    :type size: int
    :return: Random alphanumeric nanoid string
    :rtype: str
    """
    return gen_id(size)
