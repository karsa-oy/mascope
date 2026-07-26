"""Unit tests for per-user temp file scoping (``api/new/temp/storage.py``).

These pin the properties that keep the ``/api/temp`` download route from
leaking one user's ephemeral files to another, or escaping the temp directory
via a crafted filename.
"""

import os

import pytest

from mascope_backend.api.new.temp import storage


@pytest.fixture
def temp_base(tmp_path, monkeypatch):
    """Point the runtime temp dir at a throwaway location for the test."""
    monkeypatch.setattr(
        storage.runtime.env,
        "path",
        lambda *segments: os.path.join(str(tmp_path), *segments),
    )
    return tmp_path


def test_user_temp_dir_is_per_user(temp_base):
    """Each user gets a distinct, real directory."""
    dir_a = storage.user_temp_dir(1)
    dir_b = storage.user_temp_dir(2)
    assert dir_a != dir_b
    assert os.path.isdir(dir_a)
    assert os.path.isdir(dir_b)


def test_user_temp_path_resolves_inside_user_dir(temp_base):
    """A plain filename resolves to a file directly in the user's dir."""
    path = storage.user_temp_path(7, "export.csv")
    assert path == os.path.join(storage.user_temp_dir(7), "export.csv")


def test_create_false_does_not_mint_directories(temp_base):
    """The read path (create=False) must not create per-user directories.

    Otherwise any authenticated GET probe against /api/temp would leave an
    empty directory behind for the probed user id.
    """
    path = storage.user_temp_path(999, "probe.csv", create=False)
    assert not os.path.isdir(storage.user_temp_dir(999, create=False))
    # The resolved path is still correct for the containment check.
    assert path == os.path.join(storage.user_temp_dir(999, create=False), "probe.csv")


@pytest.mark.parametrize(
    "attack",
    [
        "../8/secret.csv",  # a sibling user's directory
        "../../secrets/jwt_secret_key.txt",  # the secrets dir
        "/etc/passwd",  # absolute path
        "foo/bar.csv",  # nested path
        "..",
        ".",
        "",
    ],
)
def test_user_temp_path_never_escapes_user_dir(temp_base, attack):
    """A crafted filename either raises or collapses to the user's own dir.

    In no case may it resolve to a path outside the requesting user's temp
    directory (another user's dir, the secrets dir, the filesystem root).
    """
    base = os.path.realpath(storage.user_temp_dir(7))
    try:
        resolved = os.path.realpath(storage.user_temp_path(7, attack))
    except ValueError:
        return
    assert os.path.dirname(resolved) == base
