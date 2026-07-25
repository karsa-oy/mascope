"""
Tests for the optional GlitchTip/Sentry error sink (`mascope_runtime.logging`).

The sink is entirely gated on ``MASCOPE_SENTRY_DSN`` and forwards WARNING+ loguru
records to GlitchTip via ``sentry-sdk``. These tests inject a fake ``sentry_sdk``
into ``sys.modules`` so they run without the optional ``sentry`` extra installed,
and cover: the default-OFF gate, init wiring/idempotency, the WARNING+ capture
paths (message vs exception), the SDK-loop guard, and never-raise behavior. One
test drives a real loguru logger end to end.
"""

import sys
import types

import pytest

import mascope_runtime.logging as rl


# --- fake sentry_sdk -------------------------------------------------------


class _FakeScope:
    def __init__(self):
        self.level = None
        self.tags = {}

    def set_level(self, value):
        self.level = value

    def set_tag(self, key, value):
        self.tags[key] = value

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _install_fake_sentry():
    """Build a fake sentry_sdk (+ integration submodules) and register it."""
    mod = types.ModuleType("sentry_sdk")
    mod.init_calls = []
    mod.captured = []
    mod.last_scope = None

    def init(**kwargs):
        mod.init_calls.append(kwargs)

    def new_scope():
        mod.last_scope = _FakeScope()
        return mod.last_scope

    def capture_exception(error=None, **kwargs):
        mod.captured.append(("exc", error))

    def capture_message(message, level=None, **kwargs):
        mod.captured.append(("msg", message, level))

    mod.init = init
    mod.new_scope = new_scope
    mod.capture_exception = capture_exception
    mod.capture_message = capture_message

    sys.modules["sentry_sdk"] = mod
    sys.modules["sentry_sdk.integrations"] = types.ModuleType("sentry_sdk.integrations")
    for sub, cls in (
        ("fastapi", "FastApiIntegration"),
        ("starlette", "StarletteIntegration"),
        ("loguru", "LoguruIntegration"),
    ):
        submod = types.ModuleType(f"sentry_sdk.integrations.{sub}")
        setattr(submod, cls, type(cls, (), {"__init__": lambda self, *a, **k: None}))
        sys.modules[f"sentry_sdk.integrations.{sub}"] = submod
    return mod


@pytest.fixture
def fake_sentry(monkeypatch):
    """Inject a fake sentry_sdk and reset the one-time init guard."""
    monkeypatch.setattr(rl, "_sentry_ready", False)
    mod = _install_fake_sentry()
    yield mod
    for name in (
        "sentry_sdk",
        "sentry_sdk.integrations",
        "sentry_sdk.integrations.fastapi",
        "sentry_sdk.integrations.starlette",
        "sentry_sdk.integrations.loguru",
    ):
        sys.modules.pop(name, None)


# --- fake loguru record ----------------------------------------------------


class _Level:
    def __init__(self, name):
        self.name = name


class _Exc:
    def __init__(self, type_, value, traceback):
        self.type = type_
        self.value = value
        self.traceback = traceback


class _Message:
    def __init__(self, record):
        self.record = record


def _msg(name="app.module", level="ERROR", message="boom", exc=None):
    return _Message(
        {"name": name, "level": _Level(level), "message": message, "exception": exc}
    )


# --- _init_sentry ----------------------------------------------------------


def test_init_off_by_default(monkeypatch):
    monkeypatch.delenv("MASCOPE_SENTRY_DSN", raising=False)
    monkeypatch.setattr(rl, "_sentry_ready", False)
    assert rl._init_sentry("prod", "v1.0.0") is False


def test_init_enables_with_dsn(monkeypatch, fake_sentry):
    monkeypatch.setenv("MASCOPE_SENTRY_DSN", "http://key@host:8000/1")
    assert rl._init_sentry("prod", "v1.2.3") is True

    assert len(fake_sentry.init_calls) == 1
    call = fake_sentry.init_calls[0]
    assert call["dsn"] == "http://key@host:8000/1"
    assert call["environment"] == "prod"
    assert call["release"] == "v1.2.3"
    assert call["traces_sample_rate"] == 0.0
    assert call["send_default_pii"] is False


def test_init_is_idempotent(monkeypatch, fake_sentry):
    monkeypatch.setenv("MASCOPE_SENTRY_DSN", "http://key@host:8000/1")
    assert rl._init_sentry("prod", None) is True
    assert rl._init_sentry("prod", None) is True
    assert len(fake_sentry.init_calls) == 1  # not re-initialized


def test_init_missing_sdk_returns_false(monkeypatch):
    monkeypatch.setenv("MASCOPE_SENTRY_DSN", "http://key@host:8000/1")
    monkeypatch.setattr(rl, "_sentry_ready", False)
    # sys.modules[name] = None makes `import name` raise ImportError.
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)
    assert rl._init_sentry("prod", None) is False


# --- _sentry_sink ----------------------------------------------------------


def test_sink_captures_exception(fake_sentry):
    err = ValueError("nope")
    rl._sentry_sink(_msg(level="ERROR", exc=_Exc(ValueError, err, None)))

    assert fake_sentry.captured == [("exc", (ValueError, err, None))]
    assert fake_sentry.last_scope.level == "error"
    assert fake_sentry.last_scope.tags["log_level"] == "ERROR"
    assert fake_sentry.last_scope.tags["logger"] == "app.module"


def test_sink_captures_message_without_exception(fake_sentry):
    rl._sentry_sink(_msg(level="WARNING", message="disk almost full", exc=None))

    assert fake_sentry.captured == [("msg", "disk almost full", None)]
    assert fake_sentry.last_scope.level == "warning"


def test_sink_maps_critical_to_fatal(fake_sentry):
    rl._sentry_sink(_msg(level="CRITICAL", exc=None))
    assert fake_sentry.last_scope.level == "fatal"


@pytest.mark.parametrize("name", ["sentry_sdk.errors", "urllib3.connectionpool"])
def test_sink_loop_guard_skips_sdk_records(fake_sentry, name):
    rl._sentry_sink(
        _msg(name=name, level="ERROR", exc=_Exc(ValueError, ValueError(), None))
    )
    assert fake_sentry.captured == []


def test_sink_never_raises(fake_sentry):
    def _boom(*a, **k):
        raise RuntimeError("transport down")

    fake_sentry.capture_message = _boom
    fake_sentry.capture_exception = _boom
    # Must swallow the transport error rather than propagate out of the sink.
    rl._sentry_sink(_msg(level="ERROR", message="x", exc=None))


# --- end-to-end through a real loguru logger -------------------------------


def test_sink_via_real_loguru(fake_sentry):
    from loguru import logger

    sink_id = logger.add(rl._sentry_sink, level="WARNING", enqueue=False, catch=False)
    try:
        try:
            raise ValueError("boom")
        except ValueError:
            logger.exception("work failed")  # -> capture_exception (has traceback)
        logger.warning("plain warning")  # -> capture_message
        logger.info("ignored below threshold")  # -> nothing (INFO < WARNING)
    finally:
        logger.remove(sink_id)

    kinds = [c[0] for c in fake_sentry.captured]
    assert kinds == ["exc", "msg"]
