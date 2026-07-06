"""
Tests for the shared PostgreSQL CLI helpers (`mascope_cli.pg.utils`).

These helpers sit under both `mascope dev db` and `mascope prod db`; the
directory helpers in particular guard against Docker creating root-owned
bind-mount directories. Docker itself is never touched — container checks
run against a mocked `subprocess.run`.
"""

import shutil
import subprocess

import pytest

from mascope_cli.pg import utils as pg_utils


@pytest.fixture
def clean_database_dir(mascope_home):
    """Ensure .runtime/database does not exist before or after the test."""
    db_root = mascope_home / ".runtime" / "database"
    shutil.rmtree(db_root, ignore_errors=True)
    yield db_root
    shutil.rmtree(db_root, ignore_errors=True)


# --- check_data_dirs ---


def test_check_data_dirs_creates_bind_mounts(clean_database_dir):
    pg_utils.check_data_dirs("prod")

    assert (clean_database_dir / "prod").is_dir()
    assert (clean_database_dir / "backups" / "prod").is_dir()
    assert (clean_database_dir / "transfer").is_dir()


def test_check_data_dirs_is_idempotent(clean_database_dir):
    pg_utils.check_data_dirs("dev")
    pg_utils.check_data_dirs("dev")  # must not raise on existing dirs

    assert (clean_database_dir / "dev").is_dir()


def test_check_data_dirs_rejects_non_directory(clean_database_dir):
    clean_database_dir.mkdir(parents=True)
    (clean_database_dir / "dev").write_text("not a directory")

    with pytest.raises(RuntimeError, match="non-directory"):
        pg_utils.check_data_dirs("dev")


# --- dirs ---


def test_dirs_resolves_backups_for_mode(mascope_home):
    host_path, mount = pg_utils.dirs(transfer=False, mode="prod")

    assert host_path == mascope_home / ".runtime" / "database" / "backups" / "prod"
    assert mount == "/backups"


def test_dirs_resolves_shared_transfer(mascope_home):
    host_path, mount = pg_utils.dirs(transfer=True, mode="prod")

    assert host_path == mascope_home / ".runtime" / "database" / "transfer"
    assert mount == "/transfer"


# --- container checks (docker mocked) ---


def _fake_docker_ps(monkeypatch, stdout: str):
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(pg_utils.subprocess, "run", fake_run)


def test_is_container_running_matches_name(monkeypatch):
    _fake_docker_ps(monkeypatch, "mascope_dev_postgres\n")
    assert pg_utils.is_container_running("dev") is True


def test_is_container_running_empty_output(monkeypatch):
    _fake_docker_ps(monkeypatch, "")
    assert pg_utils.is_container_running("dev") is False


def test_is_container_running_without_docker_binary(monkeypatch):
    def fake_run(args, **kwargs):
        raise FileNotFoundError("docker not installed")

    monkeypatch.setattr(pg_utils.subprocess, "run", fake_run)
    assert pg_utils.is_container_running("dev") is False


# --- validate_env ---


def test_validate_env_accepts_existing_env(mascope_home):
    assert pg_utils.validate_env("default") is True


def test_validate_env_rejects_unknown_env(mascope_home):
    assert pg_utils.validate_env("does-not-exist") is False


def test_validate_env_sees_new_env_dirs(mascope_home):
    env_dir = mascope_home / ".runtime" / "env" / "tof1"
    env_dir.mkdir()
    try:
        assert pg_utils.validate_env("tof1") is True
    finally:
        env_dir.rmdir()
