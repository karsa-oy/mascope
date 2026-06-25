"""
End-to-end reproducibility tests for the published demo dataset.

These are the infrastructure-dependent layers (they live under the backend test
harness, which requires the dev stack + secrets to collect):

1. **Bundle integrity**: asserts the cached demo bundle matches its manifest
   checksums (skips if no bundle is cached).
2. **Full pipeline**: re-runs ingestion + matching from the bundle's raw files
   and asserts the produced peaks reproduce the golden outputs within the
   manifest tolerances. Skipped until the live export seam is wired - see
   ``docs/demo_dataset.md``.

The pure comparison logic (``compare_peaks``) is tested separately and without
any infrastructure in ``tooling/cli/tests/test_demo_verify.py``.
"""

import pytest

from mascope_cli.cmd.demo import bundles


def test_cached_bundle_matches_manifest():
    """If a demo bundle is cached locally, it must match its manifest checksums."""
    if not bundles.is_cached():
        pytest.skip("no demo bundle cached; run 'mascope demo fetch' first")
    problems = bundles.verify_manifest()
    assert problems == [], f"bundle integrity issues: {problems}"


@pytest.mark.skip(reason="requires a live rebuilt demo stack; see docs/demo_dataset.md")
def test_pipeline_reproduces_goldens():
    """
    Re-run the full ingestion + matching pipeline from the bundle's raw files
    and assert the produced peaks reproduce the golden outputs within the
    manifest tolerances.

    The export + comparison seams now exist:
    ``mascope_backend.db.scripts.export_goldens.get_golden_peaks`` reads the
    produced peaks and ``demo.verify.compare_peaks`` asserts them against
    ``expected/peaks.parquet`` (keyed on ``target_isotope_formula``). What
    remains is the heavy stack orchestration this test would drive: stage raw ->
    run converter -> wait for ingestion -> trigger matching -> get_golden_peaks
    -> compare_peaks. Tracked in docs/demo_dataset.md.
    """
    raise NotImplementedError
