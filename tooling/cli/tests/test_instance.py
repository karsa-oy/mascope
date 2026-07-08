"""
Tests for the per-worktree instance registry (``mascope_cli.instance``).

Hermetic: the registry is a JSON file under a temp home, so no Docker,
Postgres, or real ``MASCOPE_PATH`` is needed. ``worktree`` and ``home`` are
passed explicitly to keep allocation deterministic.
"""

import json

import pytest

from mascope_cli import instance as inst


def _alloc(home, path):
    return inst.resolve_or_allocate(worktree=path, home=home)


def test_allocates_slot_zero_and_derives_ports(tmp_path):
    got = _alloc(tmp_path, "/work/alice")

    assert got.slot == 0
    assert got.env == "wt-alice"
    assert got.api_port == inst.API_PORT_BASE
    assert got.frontend_port == inst.FRONTEND_PORT_BASE


def test_second_worktree_gets_next_slot(tmp_path):
    first = _alloc(tmp_path, "/work/alice")
    second = _alloc(tmp_path, "/work/bob")

    assert (first.slot, second.slot) == (0, 1)
    assert second.env == "wt-bob"
    assert second.api_port == inst.API_PORT_BASE + 1
    assert second.frontend_port == inst.FRONTEND_PORT_BASE + 1


def test_same_worktree_is_idempotent(tmp_path):
    first = _alloc(tmp_path, "/work/alice")
    again = _alloc(tmp_path, "/work/alice")

    assert first == again
    assert len(inst.list_instances(home=tmp_path)) == 1


def test_env_name_disambiguated_on_basename_clash(tmp_path):
    a = _alloc(tmp_path, "/work/one/proj")
    b = _alloc(tmp_path, "/work/two/proj")

    assert a.env == "wt-proj"
    assert b.env != a.env
    assert b.env.startswith("wt-proj-")


def test_release_frees_slot_for_reuse(tmp_path):
    _alloc(tmp_path, "/work/alice")  # slot 0
    bob = _alloc(tmp_path, "/work/bob")  # slot 1

    released = inst.release(bob.env, home=tmp_path)
    assert released.slot == 1

    reused = _alloc(tmp_path, "/work/carol")
    assert reused.slot == 1  # lowest free slot is reclaimed


def test_release_unknown_env_returns_none(tmp_path):
    assert inst.release("wt-nope", home=tmp_path) is None


def test_registry_persists_to_disk(tmp_path):
    _alloc(tmp_path, "/work/alice")

    registry = json.loads((tmp_path / ".runtime" / "instances.json").read_text())
    [record] = registry["instances"].values()
    assert record == {
        "slot": 0,
        "env": "wt-alice",
        "api_port": inst.API_PORT_BASE,
        "frontend_port": inst.FRONTEND_PORT_BASE,
    }


def test_provision_creates_env_dir(tmp_path):
    got = _alloc(tmp_path, "/work/alice")
    inst.provision(got, home=tmp_path)

    assert (tmp_path / ".runtime" / "env" / "wt-alice").is_dir()


def test_max_slots_exhausted_raises(tmp_path):
    for i in range(inst.MAX_SLOTS):
        _alloc(tmp_path, f"/work/proj{i}")

    with pytest.raises(inst.InstanceError):
        _alloc(tmp_path, "/work/one-too-many")


def test_worktree_key_falls_back_to_cwd_outside_git(tmp_path, monkeypatch):
    # Simulate git being unavailable so the fallback path is exercised.
    def _no_git(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(inst.subprocess, "run", _no_git)

    assert inst.worktree_key(cwd=str(tmp_path)) == str(tmp_path.resolve())
