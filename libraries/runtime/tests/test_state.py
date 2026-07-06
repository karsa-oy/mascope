"""
Tests for the runtime state classes (`mascope_runtime.state`).

State is per instance: two Runtime instances in one process (e.g. the CLI's
own plus a temporary one built for a compose invocation) must not share or
clobber each other's state — the paths/dicts used to be module globals, so
the most recently constructed instance hijacked every other instance.
"""

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
