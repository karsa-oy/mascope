"""
End-to-end reproducibility tests for the published demo dataset.

Two layers:

1. **Bundle integrity** (`test_cached_bundle_matches_manifest`): asserts the
   cached demo bundle matches its manifest checksums (skips if no bundle is
   cached).
2. **Full pipeline** (`test_pipeline_reproduces_goldens`): uploads the bundle's
   raw files into a rebuild-mode demo stack, waits for the real conversion +
   peak detection + matching pipeline to finish, exports the produced peaks and
   asserts they reproduce the golden outputs within the manifest tolerances.

The pipeline test is opt-in (it boots nothing itself and takes tens of
minutes): start a rebuild-mode demo stack first, then enable it with
``MASCOPE_REPRO_TEST=1``:

    MASCOPE_DEMO_REBUILD=1 docker compose -f docker-compose.demo.yaml up -d
    MASCOPE_REPRO_TEST=1 uv run pytest server/backend/tests/system/reproducibility/ -v

CI runs it from ``.github/workflows/reproducibility.yaml`` (nightly + manual
dispatch). Configuration (all optional):

- ``MASCOPE_REPRO_APP_URL``: app origin (default ``http://127.0.0.1:8080``).
- ``MASCOPE_REPRO_BACKEND_CONTAINER`` / ``MASCOPE_REPRO_POSTGRES_CONTAINER``:
  container names (defaults match ``docker-compose.demo.yaml``).
- ``MASCOPE_REPRO_TIMEOUT``: max seconds to wait for ingestion + matching
  (default 2700).

The pure comparison logic (``compare_peaks``) is shared with ``mascope demo
verify`` and tested without any infrastructure in
``tooling/cli/tests/test_demo_verify.py``; the export seam is
``mascope_backend.db.scripts.export_goldens`` (run inside the backend
container, so capture and verification can never drift). See
``docs/demo_dataset.md`` for the full design.
"""

import json
import os
import subprocess
import time

import pytest

from mascope_cli.cmd.demo import _rebuild, bundles
from mascope_cli.cmd.demo.verify import compare_peaks


APP_URL = os.environ.get("MASCOPE_REPRO_APP_URL", "http://127.0.0.1:8080")
BACKEND_CONTAINER = os.environ.get(
    "MASCOPE_REPRO_BACKEND_CONTAINER", "mascope_demo_backend"
)
POSTGRES_CONTAINER = os.environ.get(
    "MASCOPE_REPRO_POSTGRES_CONTAINER", "mascope_demo_postgres"
)
DB_NAME = os.environ.get("MASCOPE_DB_NAME", "mascope_demo")
DB_USER = os.environ.get("MASCOPE_DB_USER", "mascope_user")
TIMEOUT_S = int(os.environ.get("MASCOPE_REPRO_TIMEOUT", "2700"))
POLL_S = 15
# The matched-peak count must be unchanged across this many consecutive polls
# after all batches settle, so matching that trails the batch status flip
# cannot produce a premature export.
STABLE_POLLS = 3

# Python of the in-image mascope uv tool (same path tooling/demo-init.sh uses).
CONTAINER_PYTHON = "/root/.local/share/uv/tools/mascope/bin/python"

requires_repro_stack = pytest.mark.skipif(
    os.environ.get("MASCOPE_REPRO_TEST") != "1",
    reason=(
        "reproducibility run not requested; boot a rebuild-mode demo stack "
        "(MASCOPE_DEMO_REBUILD=1 docker compose -f docker-compose.demo.yaml up -d) "
        "and set MASCOPE_REPRO_TEST=1"
    ),
)


def test_cached_bundle_matches_manifest():
    """If a demo bundle is cached locally, it must match its manifest checksums."""
    if not bundles.is_cached():
        pytest.skip("no demo bundle cached; run 'mascope demo fetch' first")
    problems = bundles.verify_manifest()
    assert problems == [], f"bundle integrity issues: {problems}"


@requires_repro_stack
def test_pipeline_reproduces_goldens():
    """
    Re-run the full ingestion + matching pipeline from the bundle's raw files
    and assert the produced peaks reproduce the golden outputs within the
    manifest tolerances.

    Steps: fetch + integrity-check the bundle, pin the raw reader version,
    upload every ``raw/`` file through the real upload endpoint (as the File
    Agent does), wait for conversion + peak detection + matching to settle,
    export the produced peaks via the shared golden-export seam, and compare
    against ``expected/peaks.parquet`` on the stable key
    ``(filename, target_isotope_id)``.
    """
    import pandas as pd

    # --- Resolve the bundle (raw inputs + goldens); fetch it if needed ------
    if not bundles.is_cached():
        from mascope_cli.cmd.demo import _fetch

        _fetch.fetch()
    problems = bundles.verify_manifest()
    assert problems == [], f"bundle integrity issues: {problems}"

    bundle_root = bundles.bundle_dir()
    manifest = bundles.load_manifest()

    expected_rel = manifest.get("expected", {}).get("peaks")
    assert expected_rel, (
        "bundle manifest has no expected/peaks goldens; build them with "
        "'mascope demo snapshot --update'"
    )

    _assert_raw_reader_pin(manifest)

    # --- Upload the raw files through the real upload endpoint --------------
    raws = sorted((bundle_root / "raw").glob("*.raw"))
    assert raws, f"bundle has no raw files at {bundle_root / 'raw'}"
    _upload_raws(raws)

    # --- Wait for conversion + peak detection + matching to finish ----------
    _wait_for_pipeline(n_files=len(raws))

    # --- Export the produced peaks and compare against the goldens ----------
    actual = pd.DataFrame(_export_actual_peaks())
    expected = pd.read_parquet(bundle_root / expected_rel)
    diffs = compare_peaks(
        expected=expected, actual=actual, tolerances=manifest.get("tolerances")
    )

    shown = "\n".join(f"  - {d}" for d in diffs[:50])
    if len(diffs) > 50:
        shown += f"\n  ... and {len(diffs) - 50} more"
    assert diffs == [], (
        f"pipeline did not reproduce the goldens ({len(diffs)} difference(s), "
        f"{len(actual)} produced vs {len(expected)} expected peaks):\n{shown}"
    )


# --- Helpers -----------------------------------------------------------------


def _docker(*args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a docker CLI command, captured; the caller owns returncode checks."""
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=timeout
    )


def _psql(sql: str) -> str:
    """
    Run one SQL statement in the demo Postgres container, return trimmed stdout.

    Uses the container-local socket (trust auth in the official postgres
    image), so no password or published port is needed.
    """
    res = _docker(
        "exec", POSTGRES_CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-tAc", sql
    )
    assert res.returncode == 0, (
        f"psql failed in {POSTGRES_CONTAINER} for {sql!r}:\n{res.stderr.strip()}"
    )
    return res.stdout.strip()


def _upload_raws(raws: list) -> None:
    """
    Upload raw files to the real upload endpoint, as the File Agent does.

    Reuses the rebuild uploader's fixed file-agent token + service name so the
    request shape matches ``mascope demo --rebuild`` exactly.
    """
    import mascope_sdk
    from mascope_sdk import api_post_file

    mascope_sdk.SERVICE_NAME = _rebuild._UPLOAD_SERVICE

    failed = []
    for raw in raws:
        resp = api_post_file(
            url=APP_URL,
            path=_rebuild._UPLOAD_PATH,
            access_token=_rebuild._UPLOAD_TOKEN,
            filepath=str(raw),
        )
        if resp is None:
            failed.append(raw.name)
    assert not failed, (
        f"failed to upload {len(failed)}/{len(raws)} raw file(s) to "
        f"{APP_URL}/api/{_rebuild._UPLOAD_PATH}: {failed}"
    )


def _wait_for_pipeline(n_files: int) -> None:
    """
    Poll the demo database until ingestion + matching settle, or fail.

    Done when: every uploaded file has produced sample items, at least one
    batch exists, no batch is processing, any batch failure aborts
    immediately, and the matched-peak count has been stable for
    ``STABLE_POLLS`` consecutive polls (matching can trail the batch status).
    """
    deadline = time.monotonic() + TIMEOUT_S
    last_matched = -1
    stable = 0

    while time.monotonic() < deadline:
        failed = int(_psql("SELECT count(*) FROM sample_batch WHERE status = 'failed'"))
        if failed:
            statuses = _psql(
                "SELECT status || ': ' || count(*) FROM sample_batch GROUP BY status"
            )
            pytest.fail(
                f"{failed} sample batch(es) failed during ingestion; "
                f"batch statuses:\n{statuses}\n"
                f"(inspect: docker logs mascope_demo_file_converter)"
            )

        files_done = int(
            _psql("SELECT count(DISTINCT sample_file_id) FROM sample_item")
        )
        batches = int(_psql("SELECT count(*) FROM sample_batch"))
        processing = int(
            _psql("SELECT count(*) FROM sample_batch WHERE status = 'processing'")
        )
        matched = int(
            _psql("SELECT count(*) FROM match_isotope WHERE match_score > 0")
        )

        if (
            files_done >= n_files
            and batches > 0
            and processing == 0
            and matched > 0
        ):
            stable = stable + 1 if matched == last_matched else 1
            if stable >= STABLE_POLLS:
                return
        else:
            stable = 0
        last_matched = matched
        time.sleep(POLL_S)

    pytest.fail(
        f"pipeline did not settle within {TIMEOUT_S}s: "
        f"{files_done}/{n_files} files processed, {batches} batch(es), "
        f"{processing} still processing, {matched} matched peak(s)"
    )


def _export_actual_peaks() -> list[dict]:
    """
    Export the produced peaks from inside the backend container.

    Runs the shared golden-export seam (`export_goldens --json`) in the
    backend container - the same query `mascope demo snapshot --update` uses
    to capture the goldens - and reads the JSON back out.
    """
    remote_path = "/tmp/repro_actual_peaks.json"
    res = _docker(
        "exec",
        BACKEND_CONTAINER,
        CONTAINER_PYTHON,
        "-m",
        "mascope_backend.db.scripts.export_goldens",
        "--json",
        remote_path,
    )
    assert res.returncode == 0, (
        f"golden export failed in {BACKEND_CONTAINER}:\n{res.stderr[-2000:]}"
    )
    res = _docker("exec", BACKEND_CONTAINER, "cat", remote_path)
    assert res.returncode == 0, f"could not read {remote_path}: {res.stderr.strip()}"
    rows = json.loads(res.stdout)
    assert rows, "golden export returned no matched peaks"
    return rows


def _assert_raw_reader_pin(manifest: dict) -> None:
    """
    Pin the raw reader to the version that produced the goldens.

    The manifest records ``produced_with.opentfraw_version``; a stack running a
    different reader version must fail loudly rather than produce a confusing
    peak diff. Skipped when the manifest does not declare a version.
    """
    want = (manifest.get("produced_with") or {}).get("opentfraw_version")
    if not want:
        return

    probe = (
        "import importlib.metadata as m\n"
        "for d in ('mascope-opentfraw', 'opentfraw'):\n"
        "    try:\n"
        "        print(m.version(d))\n"
        "        break\n"
        "    except m.PackageNotFoundError:\n"
        "        pass\n"
    )
    res = _docker("exec", BACKEND_CONTAINER, CONTAINER_PYTHON, "-c", probe)
    assert res.returncode == 0, f"reader version probe failed: {res.stderr.strip()}"
    have = res.stdout.strip()
    assert have == want, (
        f"raw reader version mismatch: goldens were produced with opentfraw "
        f"{want}, the stack runs {have or '(not installed)'} - regenerate the "
        f"goldens ('mascope demo snapshot --update') or align the reader version"
    )
