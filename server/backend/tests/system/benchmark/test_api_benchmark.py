"""
Read-path performance benchmarks against a scaled demo stack.

Boots nothing itself: start a demo stack, then opt in with
``MASCOPE_BENCH_TEST=1``. The suite clones the demo dataset up to a
configurable size (thousands of samples and collection ions), then exercises
the endpoints the batch overview and sample browser lean on, asserting two
kinds of budget:

- **per-request latency** - no single HTTP request may exceed
  ``MASCOPE_BENCH_REQUEST_BUDGET_S`` (default 20 s, the frontend's axios
  timeout). This is the exact failure mode that made large batches unusable;
  it is loose enough not to flake on a slow runner yet catches real blowups.
- **response size** - no single response body may exceed
  ``MASCOPE_BENCH_PAYLOAD_BUDGET_MB`` (default 12 MB). Deterministic, so it
  guards against a payload-shape regression (e.g. metadata duplicated per row)
  regardless of runner speed.

Every measurement is also written to ``$GITHUB_STEP_SUMMARY`` as a table so the
nightly job shows a trend, not just pass/fail.

    docker compose -f docker-compose.demo.yaml up -d
    MASCOPE_BENCH_TEST=1 uv run pytest server/backend/tests/system/benchmark/ -v

Configuration (all optional):

- ``MASCOPE_BENCH_APP_URL``: app origin (default ``http://127.0.0.1:8080``).
- ``MASCOPE_BENCH_POSTGRES_CONTAINER``: demo Postgres container name.
- ``MASCOPE_DB_NAME`` / ``MASCOPE_DB_USER``: demo database name / user.
- ``MASCOPE_BENCH_EMAIL`` / ``MASCOPE_BENCH_PASSWORD``: demo login.
- ``MASCOPE_BENCH_SAMPLE_MULT`` / ``MASCOPE_BENCH_ION_MULT``: clone generations
  to add (defaults 25 / 2 -> roughly 2100 samples, 1800 collection ions on the
  published bundle - well past the size that used to time out, with budget
  headroom for a shared runner). Set both to 0 to benchmark the dataset as-is.
- ``MASCOPE_BENCH_REQUEST_BUDGET_S`` / ``MASCOPE_BENCH_PAYLOAD_BUDGET_MB``:
  override the budgets above.
- ``MASCOPE_BENCH_ION_CHUNK``: ions per series request (default 100).
"""

import os
import subprocess
import time
from pathlib import Path

import pytest


APP_URL = os.environ.get("MASCOPE_BENCH_APP_URL", "http://127.0.0.1:8080")
POSTGRES_CONTAINER = os.environ.get(
    "MASCOPE_BENCH_POSTGRES_CONTAINER", "mascope_demo_postgres"
)
DB_NAME = os.environ.get("MASCOPE_DB_NAME", "mascope_demo")
DB_USER = os.environ.get("MASCOPE_DB_USER", "mascope_user")
EMAIL = os.environ.get("MASCOPE_BENCH_EMAIL", "demo@mascope.app")
PASSWORD = os.environ.get("MASCOPE_BENCH_PASSWORD", "mascope-demo")

SAMPLE_MULT = int(os.environ.get("MASCOPE_BENCH_SAMPLE_MULT", "25"))
ION_MULT = int(os.environ.get("MASCOPE_BENCH_ION_MULT", "2"))
ION_CHUNK = int(os.environ.get("MASCOPE_BENCH_ION_CHUNK", "100"))

REQUEST_BUDGET_S = float(os.environ.get("MASCOPE_BENCH_REQUEST_BUDGET_S", "20"))
PAYLOAD_BUDGET_MB = float(os.environ.get("MASCOPE_BENCH_PAYLOAD_BUDGET_MB", "12"))

EXPAND_SQL = Path(__file__).with_name("expand_demo.sql")

requires_bench_stack = pytest.mark.skipif(
    os.environ.get("MASCOPE_BENCH_TEST") != "1",
    reason=(
        "benchmark run not requested; boot a demo stack "
        "(docker compose -f docker-compose.demo.yaml up -d) and set "
        "MASCOPE_BENCH_TEST=1"
    ),
)


# --- Docker / DB helpers (demo Postgres port is not published) ---------------


def _docker(*args: str, stdin: str | None = None, timeout: int = 1800):
    """Run a docker CLI command captured, decoding as UTF-8."""
    return subprocess.run(
        ["docker", *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _psql(sql: str) -> str:
    """Run one SQL statement in the demo Postgres container, return stdout."""
    res = _docker(
        "exec", POSTGRES_CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-tAc", sql
    )
    assert res.returncode == 0, f"psql failed for {sql!r}:\n{res.stderr.strip()}"
    return res.stdout.strip()


def _psql_script(sql: str, variables: dict[str, str]) -> str:
    """Pipe a multi-statement SQL script into the demo Postgres container."""
    args = ["exec", "-i", POSTGRES_CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME]
    for key, value in variables.items():
        args += ["-v", f"{key}={value}"]
    args += ["-f", "-"]
    res = _docker(*args, stdin=sql)
    assert res.returncode == 0, f"psql script failed:\n{res.stderr.strip()}"
    return res.stdout.strip()


# --- Measurement bookkeeping -------------------------------------------------


class Measurement:
    """One timed request group, collected for the summary and asserted on."""

    def __init__(self, name: str):
        self.name = name
        self.n_requests = 0
        self.total_s = 0.0
        self.max_request_s = 0.0
        self.max_body_mb = 0.0
        self.total_body_mb = 0.0
        self.rows = 0

    def record(self, elapsed_s: float, body_bytes: int, rows: int) -> None:
        self.n_requests += 1
        self.total_s += elapsed_s
        self.max_request_s = max(self.max_request_s, elapsed_s)
        body_mb = body_bytes / 1e6
        self.max_body_mb = max(self.max_body_mb, body_mb)
        self.total_body_mb += body_mb
        self.rows += rows

    def assert_budgets(self) -> None:
        assert self.max_request_s <= REQUEST_BUDGET_S, (
            f"{self.name}: slowest request {self.max_request_s:.1f}s exceeds "
            f"the {REQUEST_BUDGET_S:.0f}s per-request budget (UI would time out)"
        )
        assert self.max_body_mb <= PAYLOAD_BUDGET_MB, (
            f"{self.name}: largest response {self.max_body_mb:.1f}MB exceeds "
            f"the {PAYLOAD_BUDGET_MB:.0f}MB payload budget"
        )


# Shared across the ordered test functions and drained by the summary fixture.
MEASUREMENTS: list[Measurement] = []


def _timed(session, method: str, path: str, **kwargs):
    """Issue a request via a requests.Session, return (response, elapsed_s)."""
    start = time.perf_counter()
    resp = session.request(method, f"{APP_URL}{path}", timeout=120, **kwargs)
    elapsed = time.perf_counter() - start
    resp.raise_for_status()
    return resp, elapsed


# --- Fixtures ----------------------------------------------------------------


@pytest.fixture(scope="module")
def bench_stack():
    """Scale the demo dataset, log in, and expose the batch/collection under test."""
    # Pick the largest batch and the largest collection attached to it, so the
    # benchmark needs no hardcoded ids (they are regenerated on every restore).
    batch_id = _psql(
        "SELECT sample_batch_id FROM sample_item "
        "GROUP BY sample_batch_id ORDER BY count(*) DESC LIMIT 1"
    )
    assert batch_id, "no sample batches in the demo database"
    collection_id = _psql(
        "SELECT tcisb.target_collection_id "
        "FROM target_collection_in_sample_batch tcisb "
        f"WHERE tcisb.sample_batch_id = '{batch_id}' "
        "ORDER BY ( "
        "  SELECT count(DISTINCT ti.target_ion_id) FROM target_ion ti "
        "  JOIN target_compound_in_target_collection tcc "
        "    ON tcc.target_compound_id = ti.target_compound_id "
        "  WHERE tcc.target_collection_id = tcisb.target_collection_id "
        ") DESC LIMIT 1"
    )
    assert collection_id, f"batch {batch_id} has no attached target collection"

    # Scale it (idempotent: deterministic ids + ON CONFLICT DO NOTHING).
    _psql_script(
        EXPAND_SQL.read_text(),
        {
            "batch": batch_id,
            "collection": collection_id,
            "mult": str(SAMPLE_MULT),
            "imult": str(ION_MULT),
        },
    )

    sample_count = int(
        _psql(f"SELECT count(*) FROM sample_item WHERE sample_batch_id = '{batch_id}'")
    )
    ion_ids = _psql(
        "SELECT DISTINCT ti.target_ion_id FROM target_ion ti "
        "JOIN target_compound_in_target_collection tcc "
        "  ON tcc.target_compound_id = ti.target_compound_id "
        f"WHERE tcc.target_collection_id = '{collection_id}'"
    ).splitlines()

    import requests

    session = requests.Session()
    resp = session.post(
        f"{APP_URL}/api/auth/login",
        data={"grant_type": "password", "username": EMAIL, "password": PASSWORD},
        timeout=60,
    )
    assert resp.status_code in (200, 204), (
        f"login as {EMAIL} failed ({resp.status_code}); is the stack up at {APP_URL}?"
    )

    yield {
        "session": session,
        "batch_id": batch_id,
        "collection_id": collection_id,
        "ion_ids": [i for i in ion_ids if i],
        "sample_count": sample_count,
    }
    session.close()


@pytest.fixture(scope="module", autouse=True)
def _write_summary():
    """After the module runs, emit a markdown table to the CI step summary."""
    yield
    if not MEASUREMENTS:
        return
    lines = [
        f"### API benchmark ({SAMPLE_MULT}x samples, {ION_MULT}x ions)",
        "",
        "| endpoint | requests | total s | slowest req s | max body MB | rows |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for m in MEASUREMENTS:
        lines.append(
            f"| {m.name} | {m.n_requests} | {m.total_s:.1f} | "
            f"{m.max_request_s:.2f} | {m.max_body_mb:.2f} | {m.rows} |"
        )
    table = "\n".join(lines) + "\n"
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write(table)
    print("\n" + table)


# --- Benchmarks --------------------------------------------------------------


@requires_bench_stack
def test_dataset_is_scaled(bench_stack):
    """Sanity: the clone step produced a genuinely large batch to benchmark."""
    if SAMPLE_MULT > 0:
        assert bench_stack["sample_count"] > 1000, (
            f"expected a scaled batch, got {bench_stack['sample_count']} samples"
        )
    assert bench_stack["ion_ids"], "collection under test has no target ions"


@requires_bench_stack
def test_samples_list(bench_stack):
    """The sample browser lists every sample in the batch in one request."""
    m = Measurement("GET /samples")
    MEASUREMENTS.append(m)
    resp, elapsed = _timed(
        bench_stack["session"],
        "GET",
        f"/api/samples?sample_batch_id={bench_stack['batch_id']}",
    )
    payload = resp.json()
    rows = len(payload.get("data") or payload.get("samples") or [])
    m.record(elapsed, len(resp.content), rows)
    m.assert_budgets()


@requires_bench_stack
def test_collection_focus_ion_aggregate(bench_stack):
    """Focusing a collection loads its batch-level best-match ion aggregate."""
    m = Measurement("POST /match/records/ion (batch aggregate)")
    MEASUREMENTS.append(m)
    resp, elapsed = _timed(
        bench_stack["session"],
        "POST",
        "/api/match/records/ion",
        json={
            "sample_batch_id": bench_stack["batch_id"],
            "target_collection_id": bench_stack["collection_id"],
        },
    )
    m.record(elapsed, len(resp.content), resp.json().get("results", 0))
    m.assert_budgets()


@requires_bench_stack
def test_chart_series_full_load(bench_stack):
    """Loading chart datapoints for the whole collection, chunked as the UI does."""
    m = Measurement("POST /match/records/ion/series (chart data)")
    MEASUREMENTS.append(m)
    ion_ids = bench_stack["ion_ids"]
    for i in range(0, len(ion_ids), ION_CHUNK):
        chunk = ion_ids[i : i + ION_CHUNK]
        resp, elapsed = _timed(
            bench_stack["session"],
            "POST",
            "/api/match/records/ion/series",
            json={
                "sample_batch_id": bench_stack["batch_id"],
                "target_ion_ids": chunk,
            },
        )
        points = sum(
            len(r["match_series"]["sample_item_ids"]) for r in resp.json()["data"]
        )
        m.record(elapsed, len(resp.content), points)
    m.assert_budgets()
