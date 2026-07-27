"""
Tests for the runtime state classes (`mascope_runtime.state`).

State is per instance: two Runtime instances in one process (e.g. the CLI's
own plus a temporary one built for a compose invocation) must not share or
clobber each other's state — the paths/dicts used to be module globals, so
the most recently constructed instance hijacked every other instance.
"""

import json
import os
import threading

import pytest

from mascope_runtime.state import RuntimeJsonState, RuntimeTempState


@pytest.fixture(autouse=True)
def _no_env_override(monkeypatch):
    """MASCOPE_ENV takes precedence over state; keep it out of these tests."""
    monkeypatch.delenv("MASCOPE_ENV", raising=False)


def _make_state(root) -> RuntimeJsonState:
    (root / ".runtime").mkdir(parents=True, exist_ok=True)
    return RuntimeJsonState(str(root))


# --- RuntimeJsonState ---


def test_json_state_creates_defaults_on_first_access(tmp_path):
    state = _make_state(tmp_path)

    assert state.mode == "dev"
    assert state.env == "default"
    assert (tmp_path / ".runtime" / "state.json").exists()


def test_json_state_persists_across_instances(tmp_path):
    _make_state(tmp_path).env = "tof1"

    assert RuntimeJsonState(str(tmp_path)).env == "tof1"


def test_json_state_override_wins_until_cleared(tmp_path):
    state = _make_state(tmp_path)

    state.override("env", "temporary")
    assert state.env == "temporary"

    state.override("env", None)
    assert state.env == "default"


def test_mascope_env_var_beats_state(tmp_path, monkeypatch):
    state = _make_state(tmp_path)
    state.env = "from-state"

    monkeypatch.setenv("MASCOPE_ENV", "from-env")

    assert state.env == "from-env"


def test_json_states_do_not_share_paths(tmp_path):
    a = _make_state(tmp_path / "a")
    b = _make_state(tmp_path / "b")

    a.env = "env-a"
    b.env = "env-b"

    assert a.env == "env-a"
    assert b.env == "env-b"


# --- Concurrent access ---
#
# The state file is shared by every process using one MASCOPE_PATH, and each
# CLI invocation writes it at startup (the entrypoint clears the env
# override). A backup cron and a monitoring cron starting the same second used
# to be enough for one to read the file while the other had truncated it,
# killing the reader with an unhandled JSONDecodeError.


@pytest.mark.parametrize(
    "corrupt",
    ["", '{"env": {"acti', "\x00\x00\x00", "not json at all"],
    ids=["empty", "partial", "nul-bytes", "garbage"],
)
def test_unreadable_state_falls_back_to_defaults(tmp_path, corrupt):
    state = _make_state(tmp_path)
    state.env = "tof1"
    (tmp_path / ".runtime" / "state.json").write_text(corrupt)

    assert state.env == "default"
    assert state.mode == "dev"


def test_unreadable_state_is_repaired_by_the_next_write(tmp_path):
    state = _make_state(tmp_path)
    (tmp_path / ".runtime" / "state.json").write_text('{"env": {"acti')

    state.env = "tof1"

    assert state.env == "tof1"
    assert json.loads((tmp_path / ".runtime" / "state.json").read_text())


def test_fallback_does_not_mutate_the_module_defaults(tmp_path):
    state = _make_state(tmp_path)
    (tmp_path / ".runtime" / "state.json").write_text("")

    state.env = "tof1"

    assert RuntimeJsonState(str(tmp_path)).env == "tof1"
    # A second, unrelated home must still start from a pristine "default".
    assert _make_state(tmp_path / "other").env == "default"


def test_readers_never_observe_a_partial_file(tmp_path, monkeypatch):
    """The destination holds valid JSON at every moment during a write."""
    state = _make_state(tmp_path)
    state_path = tmp_path / ".runtime" / "state.json"
    assert state.env == "default"  # materialize the file before spying
    seen = []
    real_replace = os.replace

    def spy(src, dst):
        # Whatever a reader would find in the instant before the swap.
        seen.append(state_path.read_text())
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    state.env = "tof1"

    assert seen and all(json.loads(text) for text in seen)
    assert seen[-1] != state_path.read_text()  # the swap did happen


def test_writes_leave_no_temp_files_behind(tmp_path):
    state = _make_state(tmp_path)

    for i in range(5):
        state.env = f"env-{i}"
        state.override("mode", "prod")

    assert [p.name for p in (tmp_path / ".runtime").iterdir()] == ["state.json"]


def test_failed_write_leaves_neither_temp_files_nor_damage(tmp_path, monkeypatch):
    state = _make_state(tmp_path)
    state.env = "tof1"

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(json, "dump", boom)
    with pytest.raises(OSError):
        state.env = "tof2"

    monkeypatch.undo()
    assert [p.name for p in (tmp_path / ".runtime").iterdir()] == ["state.json"]
    assert state.env == "tof1"  # the previous good state is untouched


def test_concurrent_readers_and_writers_do_not_crash(tmp_path):
    """Regression test for the crons-in-the-same-second production crash."""
    state = _make_state(tmp_path)
    state.env = "default"
    errors = []
    start = threading.Barrier(6)

    def write():
        start.wait()
        for i in range(30):
            try:
                state.override("env", f"env-{i}")
            except Exception as error:  # noqa: BLE001 - the test is the assert
                errors.append(error)

    def read():
        start.wait()
        for _ in range(30):
            try:
                assert state.env
            except Exception as error:  # noqa: BLE001
                errors.append(error)

    threads = [threading.Thread(target=write) for _ in range(2)]
    threads += [threading.Thread(target=read) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert json.loads((tmp_path / ".runtime" / "state.json").read_text())


# --- RuntimeTempState ---


def test_temp_state_defaults_and_updates():
    state = RuntimeTempState(None, None)

    assert state.env == "default"
    assert state.mode == "dev"

    state.mode = "prod"
    assert state.mode == "prod"


def test_temp_state_override_does_not_touch_active():
    state = RuntimeTempState("default", "dev")

    state.override("mode", "prod")
    assert state.mode == "prod"

    state.override("mode", None)
    assert state.mode == "dev"


def test_temp_states_are_independent():
    a = RuntimeTempState("env-a", "dev")
    b = RuntimeTempState("env-b", "prod")

    a.override("mode", "test")

    assert a.mode == "test"
    assert b.mode == "prod"
    assert a.env == "env-a"
    assert b.env == "env-b"


def test_temp_state_is_isolated_from_json_state(tmp_path):
    json_state = _make_state(tmp_path)
    temp_state = RuntimeTempState("temp-env", "prod")

    json_state.env = "json-env"

    assert temp_state.env == "temp-env"
    assert json_state.env == "json-env"
    assert json_state.mode == "dev"
