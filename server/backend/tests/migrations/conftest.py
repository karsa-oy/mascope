"""
Test fixtures for the Alembic migrations test category (stairway test).

This conftest is intentionally self-contained and does NOT use the async
machinery from the root conftest. Reasons:

- Alembic is a sync API. `alembic.command.upgrade/downgrade` cannot be
  called from async code without thread offloading, which adds nothing
  here since these tests don't share fixtures with the application stack.
- The migrations test does not need `patch_db` — it never touches
  `ASYNC_SESSION_MAKER` or the application's DB session machinery. It
  only exercises raw DDL via Alembic.
- The schema must be built by Alembic (`alembic upgrade`), not
  `Base.metadata.create_all` — the whole point is testing the migration
  scripts, not the ORM models. So this category cannot share the test DB
  lifecycle from `async_engine_factory`.

Design:
- One ephemeral database `mascope_test_migrations`, created fresh at
  session start and dropped on teardown.
- Sync `psycopg2` driver, matching `DatabaseConfig.get_postgres_url_sync`
  and `db-init.sh`.
- Alembic `Config` is built programmatically, pointed at the existing
  `alembic.ini` for `script_location` and post_write_hooks settings, with
  `sqlalchemy.url` overridden to the test database URL. The patched
  `env.py._resolve_url()` honors this override.

Credentials are resolved via `test_utils.get_test_password` and friends —
the same helpers used by the root conftest, so dev/CI behavior is
identical to the rest of the test suite.
"""

import os
from pathlib import Path
from typing import Iterator

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool
from test_utils import (
    get_test_db_host,
    get_test_db_port,
    get_test_db_user,
    get_test_password,
)


# --- Constants ---

BACKEND_PATH = Path(os.environ["MASCOPE_PATH"]) / "server" / "backend"
ALEMBIC_INI = BACKEND_PATH / "alembic.ini"

STAIRWAY_DB_NAME = "mascope_test_migrations"


# --- URL builders (sync, psycopg2 — matches DatabaseConfig.get_postgres_url_sync) ---


def _sync_url(db_name: str) -> str:
    """Build sync psycopg2 URL for `db_name`.

    Matches the format produced by `DatabaseConfig.get_postgres_url_sync`,
    so the test exercises the same driver as dev/prod migrations.
    """
    return (
        f"postgresql+psycopg2://{get_test_db_user()}:{get_test_password()}"
        f"@{get_test_db_host()}:{get_test_db_port()}/{db_name}"
    )


def _admin_url() -> str:
    """Build sync admin URL pointing at the `postgres` maintenance DB."""
    return _sync_url("postgres")


# --- DB lifecycle helpers ---


def _drop_database(admin_engine: Engine, db_name: str) -> None:
    """Terminate connections and drop `db_name` if it exists.

    Uses the same `pg_terminate_backend` pattern as the async factory in
    the root conftest — necessary because a leftover connection (from a
    previous failed run) blocks `DROP DATABASE`.
    """
    with admin_engine.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :db AND pid <> pg_backend_pid()"
            ),
            {"db": db_name},
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))


def _ephemeral_db(db_name: str) -> Iterator[str]:
    """Drop+create `db_name` and yield its sync URL; drop again on teardown.

    Shared lifecycle used by both the stairway and drift databases.
    The DB is created empty — no schema, no `alembic_version` table.
    """
    admin_engine = create_engine(
        _admin_url(), poolclass=NullPool, isolation_level="AUTOCOMMIT"
    )
    try:
        _drop_database(admin_engine, db_name)
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))

        yield _sync_url(db_name)

    finally:
        _drop_database(admin_engine, db_name)
        admin_engine.dispose()


# --- Stairway fixtures ---


@pytest.fixture(scope="session")
def stairway_db_url() -> Iterator[str]:
    """Session-scoped: drop+create `mascope_test_migrations`, drop on teardown.

    Used by the stairway test exclusively. State accumulates across the
    parametrize chain — after revision N is applied, the DB is at N and
    the next step starts there.
    """
    yield from _ephemeral_db(STAIRWAY_DB_NAME)


@pytest.fixture(scope="session")
def stairway_alembic_config(stairway_db_url: str) -> Config:
    """Programmatic Alembic Config pointed at the stairway test database.

    Loads `alembic.ini` for `script_location` and post_write_hooks, but
    overrides `sqlalchemy.url`. The patched `env.py._resolve_url()` honors
    this override and skips the runtime-derived URL — that's what isolates
    the test from whichever Mascope env is active.

    Named `stairway_alembic_config` (not `alembic_config`) to avoid
    colliding with the pytest-alembic fixture of the same name used by
    the drift test.
    """
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", stairway_db_url)
    return cfg
