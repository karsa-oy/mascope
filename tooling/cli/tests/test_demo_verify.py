"""
Unit tests for the demo reproducibility comparator (``compare_peaks``).

Pure logic - no database, stack, or secrets required. These run standalone:

    uv run pytest tooling/cli/tests/test_demo_verify.py
"""

import pandas as pd

from mascope_cli.cmd.demo.verify import compare_peaks


def _peaks(rows: list[tuple]) -> pd.DataFrame:
    """Build a peaks frame from ``(mz, height, area, formula)`` tuples."""
    return pd.DataFrame(
        rows, columns=["mz", "height", "area", "target_compound_formula"]
    )


def test_identical_peaks_reproduce():
    """Identical inputs produce no differences."""
    golden = _peaks(
        [(180.0634, 1000.0, 5000.0, "CH4N2O"), (78.9183, 800.0, 4000.0, "Br")]
    )
    assert compare_peaks(golden, golden.copy()) == []


def test_mz_within_tolerance_passes():
    """A sub-ppm m/z shift is within the default 1 ppm tolerance."""
    golden = _peaks([(180.0634, 1000.0, 5000.0, "CH4N2O")])
    actual = _peaks([(180.0634 * (1 + 0.5e-6), 1000.0, 5000.0, "CH4N2O")])
    assert compare_peaks(golden, actual) == []


def test_mz_outside_tolerance_flagged():
    """An m/z shift beyond tolerance is reported as a missing match."""
    golden = _peaks([(180.0634, 1000.0, 5000.0, "CH4N2O")])
    actual = _peaks([(180.0634 * (1 + 5e-6), 1000.0, 5000.0, "CH4N2O")])  # +5 ppm
    problems = compare_peaks(golden, actual, tolerances={"mz_ppm": 1.0})
    assert any("ppm" in p for p in problems)


def test_intensity_drift_flagged():
    """Intensity beyond the relative tolerance is reported."""
    golden = _peaks([(180.0634, 1000.0, 5000.0, "CH4N2O")])
    actual = _peaks([(180.0634, 1100.0, 5000.0, "CH4N2O")])  # +10%
    problems = compare_peaks(golden, actual, tolerances={"intensity_rel": 0.01})
    assert any("intensity" in p for p in problems)


def test_area_drift_flagged():
    """Area beyond the relative tolerance is reported."""
    golden = _peaks([(180.0634, 1000.0, 5000.0, "CH4N2O")])
    actual = _peaks([(180.0634, 1000.0, 5500.0, "CH4N2O")])  # +10%
    problems = compare_peaks(golden, actual, tolerances={"area_rel": 0.02})
    assert any("area" in p for p in problems)


def test_missing_compound_flagged():
    """A golden compound absent from the actual set is reported."""
    golden = _peaks(
        [(180.0634, 1000.0, 5000.0, "CH4N2O"), (78.9183, 800.0, 4000.0, "Br")]
    )
    actual = _peaks([(180.0634, 1000.0, 5000.0, "CH4N2O")])
    problems = compare_peaks(golden, actual)
    assert any("Br" in p for p in problems)


def test_empty_actual_flagged():
    """No produced peaks is a hard failure."""
    golden = _peaks([(180.0634, 1000.0, 5000.0, "CH4N2O")])
    assert compare_peaks(golden, _peaks([])) != []
