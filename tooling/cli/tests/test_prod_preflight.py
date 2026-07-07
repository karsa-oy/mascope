"""
Tests for the `mascope prod update --check` preflight classifier.

The classifier decides whether a pending update is a no-op, a fast (image-only)
update, or a migration update that needs a maintenance window. Getting that
call right is the whole point of the preflight, so the pure classification and
the plan-building seams are covered here with docker fully stubbed.
"""

import pytest

import mascope_cli.cmd.prod.preflight as preflight


_HEAD = "abc123def456"

# Shared build_plan kwargs; individual tests override the pieces they exercise.
_PLAN_KWARGS = dict(
    target="v1.3.0",
    backend_image="backend:v1.3.0",
    backend_container="mascope_prod_backend",
    frontend_image="frontend:v1.3.0",
    frontend_container="mascope_prod_frontend",
    pg_container="mascope_prod_postgres",
    db_user="mascope_user",
    db_name="mascope_default",
    pull=False,
)


@pytest.mark.parametrize(
    "image_changed, migration_pending, expected",
    [
        (False, False, "up-to-date"),
        (True, False, "fast-update"),
        (False, True, "migration-update"),
        (True, True, "migration-update"),  # a migration always wins
    ],
)
def test_classify(image_changed, migration_pending, expected):
    assert preflight.classify(image_changed, migration_pending) == expected


def _stub(monkeypatch, *, head, current, image_changed):
    monkeypatch.setattr(preflight, "image_alembic_head", lambda image: head)
    monkeypatch.setattr(preflight, "db_current_revision", lambda *a, **k: current)
    monkeypatch.setattr(
        preflight, "_image_changed", lambda image, container: image_changed
    )


def test_build_plan_up_to_date(monkeypatch):
    _stub(monkeypatch, head=_HEAD, current=_HEAD, image_changed=False)
    plan = preflight.build_plan(**_PLAN_KWARGS)
    assert plan.classification == "up-to-date"
    assert plan.migration_pending is False
    assert plan.image_changed is False
    assert plan.exit_code == 0


def test_build_plan_fast_update(monkeypatch):
    _stub(monkeypatch, head=_HEAD, current=_HEAD, image_changed=True)
    plan = preflight.build_plan(**_PLAN_KWARGS)
    assert plan.classification == "fast-update"
    assert plan.migration_pending is False
    assert plan.exit_code == 10


def test_build_plan_migration_update(monkeypatch):
    _stub(monkeypatch, head=_HEAD, current="000000aaaaaa", image_changed=False)
    plan = preflight.build_plan(**_PLAN_KWARGS)
    assert plan.classification == "migration-update"
    assert plan.migration_pending is True
    assert plan.current_revision == "000000aaaaaa"
    assert plan.target_revision == _HEAD
    assert plan.exit_code == 20


def test_build_plan_fresh_db_is_migration(monkeypatch):
    # A database with no alembic_version yet reads as None and must classify as
    # a migration update — the first migration will run on startup.
    _stub(monkeypatch, head=_HEAD, current=None, image_changed=True)
    plan = preflight.build_plan(**_PLAN_KWARGS)
    assert plan.classification == "migration-update"
    assert plan.current_revision is None


def test_build_plan_pull_failure_raises(monkeypatch):
    monkeypatch.setattr(preflight, "pull_image", lambda image: False)
    with pytest.raises(preflight.PreflightError):
        preflight.build_plan(**{**_PLAN_KWARGS, "pull": True})


def test_build_plan_unreadable_head_raises(monkeypatch):
    monkeypatch.setattr(preflight, "pull_image", lambda image: True)
    monkeypatch.setattr(preflight, "image_alembic_head", lambda image: None)
    with pytest.raises(preflight.PreflightError):
        preflight.build_plan(**{**_PLAN_KWARGS, "pull": True})


def test_plan_to_dict_roundtrip(monkeypatch):
    _stub(monkeypatch, head=_HEAD, current="000000aaaaaa", image_changed=True)
    plan = preflight.build_plan(**_PLAN_KWARGS)
    assert plan.to_dict() == {
        "target": "v1.3.0",
        "classification": "migration-update",
        "image_changed": True,
        "migration_pending": True,
        "current_revision": "000000aaaaaa",
        "target_revision": _HEAD,
    }


def test_image_head_parses_revision(monkeypatch):
    # `alembic heads` prints e.g. "abc123def456 (head)"; the first 12-hex token
    # is the revision, matching what db-init.sh greps for.
    class _Result:
        returncode = 0
        stdout = f"{_HEAD} (head)\n"

    monkeypatch.setattr(preflight, "_run", lambda *a, **k: _Result())
    assert preflight.image_alembic_head("backend:v1.3.0") == _HEAD


def test_image_head_none_on_failure(monkeypatch):
    class _Result:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(preflight, "_run", lambda *a, **k: _Result())
    assert preflight.image_alembic_head("backend:v1.3.0") is None
