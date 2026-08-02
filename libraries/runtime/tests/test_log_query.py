"""
Tests for log querying (`RuntimeLogging.query`).

These run real DuckDB queries against NDJSON log files written into a temp
directory shaped like a runtime env's log dir (`<base>/<mode>/<date>.<module>.log`),
and cover the agent-facing behaviors: raw NDJSON output (--json), newest-N
limiting, grep patterns containing SQL-hostile quotes, the per-service filter,
and the empty-glob case. They skip when the optional `duckdb` dependency
(`mascope_runtime[logs]`) is not installed.

Record timestamps are written with the machine's local UTC offset: naive
`--from`/`--to` values are compared in DuckDB's session timezone (the system
local zone), mirroring how the CLI is used on a server.
"""

import datetime
import json

import pytest


pytest.importorskip("duckdb")

import mascope_runtime.logging as rl  # noqa: E402


# --- fake runtime + log fixtures -------------------------------------------


class _FakeModuleConfig:
    def __init__(self, log_path):
        self.log_path = log_path
        self.log_level = "info"


class _FakeModule:
    def __init__(self, log_path):
        self.name = "cli"
        self.config = _FakeModuleConfig(log_path)


class _FakeRuntime:
    """Just enough Runtime for RuntimeLogging.query()."""

    def __init__(self, base):
        self.module = _FakeModule(base)
        self.mode = "dev"
        self.logger = rl.logger


def _time(hour, minute, second):
    """2026-06-23 HH:MM:SS in the machine's local zone, loguru-repr style."""
    naive = datetime.datetime(2026, 6, 23, hour, minute, second)
    return naive.astimezone().isoformat(sep=" ", timespec="microseconds")


def _record(time_repr, message, level="INFO", level_no=20, module="backend"):
    """One loguru-serialized NDJSON line, shaped like `serialize=True` output."""
    return {
        "text": f"{message}\n",
        "record": {
            "time": {"repr": time_repr, "timestamp": 0},
            "level": {"name": level, "no": level_no, "icon": ""},
            "message": message,
            "name": f"mascope_{module}.some.module",
            "function": "run",
            "line": 1,
            "module": "some",
            "file": {"name": "some.py", "path": "/x/some.py"},
            "process": {"id": 1, "name": "MainProcess"},
            "thread": {"id": 1, "name": "MainThread"},
            "elapsed": {"repr": "0:00:00", "seconds": 0.0},
            "exception": None,
            "extra": {"mod": module, "key": "", "status_code": "", "method": ""},
        },
    }


QUOTED_MESSAGE = 'meeting at 9 o\'clock failed: quote "test"'


@pytest.fixture
def log_env(tmp_path):
    """A log dir with backend + file-converter logs, wrapped in RuntimeLogging."""
    log_dir = tmp_path / "dev"
    log_dir.mkdir()
    backend = [_record(_time(10, 0, i), f"backend event {i}") for i in range(5)]
    backend.append(_record(_time(10, 1, 0), QUOTED_MESSAGE, level="ERROR", level_no=40))
    converter = [_record(_time(10, 0, 30), "converter event", module="file-converter")]
    _write_ndjson(log_dir / "2026-06-23.backend.log", backend)
    _write_ndjson(log_dir / "2026-06-23.file-converter.log", converter)
    return rl.RuntimeLogging(_FakeRuntime(str(tmp_path)))


def _write_ndjson(path, records):
    with open(path, "w", encoding="utf-8") as file:
        file.writelines(json.dumps(record) + "\n" for record in records)


def _json_lines(capsys):
    """Parse the captured stdout as one JSON record per line."""
    out = capsys.readouterr().out
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def _messages(capsys):
    return [line["record"]["message"] for line in _json_lines(capsys)]


# --- json output ------------------------------------------------------------


def test_json_output_is_raw_ndjson(log_env, capsys):
    log_env.query(json_output=True)

    out = capsys.readouterr().out
    lines = [json.loads(line) for line in out.splitlines() if line.strip()]
    assert len(lines) == 7  # 6 backend + 1 converter
    # raw records pass through, no summary line, no ANSI colors
    assert all("record" in line for line in lines)
    assert "Printed" not in out
    assert "\x1b[" not in out


# --- newest-N limiting ------------------------------------------------------


def test_limit_returns_most_recent_oldest_first(log_env, capsys):
    log_env.query(json_output=True, limit=2)

    # the two newest records (converter at 10:00:30, error at 10:01:00),
    # still printed in chronological order
    assert _messages(capsys) == ["converter event", QUOTED_MESSAGE]


# --- grep -------------------------------------------------------------------


def test_grep_with_single_quote_does_not_crash(log_env, capsys):
    log_env.query(json_output=True, grep="9 o'clock", grep_context=0)

    assert _messages(capsys) == [QUOTED_MESSAGE]


def test_grep_includes_context_rows(log_env, capsys):
    log_env.query(json_output=True, grep="o'clock", grep_context=2, service="backend")

    # the match plus the two preceding rows (nothing follows the match)
    assert _messages(capsys) == ["backend event 3", "backend event 4", QUOTED_MESSAGE]


# --- service filter ---------------------------------------------------------


def test_service_filter_selects_one_module(log_env, capsys):
    log_env.query(json_output=True, service="file-converter")

    assert _messages(capsys) == ["converter event"]


def test_service_with_no_files_prints_nothing(log_env, capsys):
    log_env.query(json_output=True, service="nonexistent")
    assert _json_lines(capsys) == []


def test_service_rejects_hostile_names(log_env, capsys):
    log_env.query(json_output=True, service="../../etc")
    assert _json_lines(capsys) == []


# --- level + time filters (regression) --------------------------------------


def test_level_filter(log_env, capsys):
    log_env.query(json_output=True, level="error")

    lines = _json_lines(capsys)
    assert [line["record"]["level"]["name"] for line in lines] == ["ERROR"]


def test_time_range_filter(log_env, capsys):
    log_env.query(
        json_output=True,
        from_datetime="2026-06-23 10:00:02",
        to_datetime="2026-06-23 10:00:04",
    )

    assert _messages(capsys) == [
        "backend event 2",
        "backend event 3",
        "backend event 4",
    ]


def test_interval_anchored_to_from(log_env, capsys):
    log_env.query(
        json_output=True,
        from_datetime="2026-06-23 10:00:03",
        interval="2 seconds",
        service="backend",
    )

    assert _messages(capsys) == ["backend event 3", "backend event 4"]


# --- pretty output ----------------------------------------------------------


def test_pretty_output_decodes_json_escapes(log_env, capsys):
    """The default printout must render `\\"` escapes, not show them raw."""
    sink_lines = []
    sink_id = rl.logger.add(
        lambda message: sink_lines.append(message.record["message"]),
        level="ERROR",
    )
    try:
        log_env.query(level="error")
    finally:
        rl.logger.remove(sink_id)

    assert sink_lines == [QUOTED_MESSAGE]
    assert "Printed 1 lines" in capsys.readouterr().out
