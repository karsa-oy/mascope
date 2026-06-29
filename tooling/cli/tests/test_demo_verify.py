"""
Unit tests for the demo reproducibility comparator (``compare_peaks``).

Pure logic - no database, stack, or secrets required. These run standalone:

    uv run pytest tooling/cli/tests/test_demo_verify.py

The comparator joins expected vs. actual peaks on a stable key
(``filename``, ``target_isotope_id``) and reports differences outside the
tolerances, plus any missing/unexpected peaks.
"""

import pandas as pd

from mascope_cli.cmd.demo.verify import compare_peaks


def _peaks(rows: list[tuple]) -> pd.DataFrame:
    """Build a peaks frame from ``(filename, isotope_id, formula, mz, height)``."""
    return pd.DataFrame(
        rows,
        columns=[
            "filename",
            "target_isotope_id",
            "target_isotope_formula",
            "mz",
            "height",
        ],
    )


_UREA = ("Orbion_pos_Ur.raw", "iso_urea_1", "CH5N2O+", 61.03964, 1000.0)
_BR = ("Orbion_neg_Br.raw", "iso_br_1", "Br-", 78.91839, 800.0)


def test_identical_peaks_reproduce():
    """Identical inputs produce no differences."""
    golden = _peaks([_UREA, _BR])
    assert compare_peaks(golden, golden.copy()) == []


def test_mz_within_tolerance_passes():
    """A sub-tolerance m/z shift on a matched key is within the default 0.1 ppm."""
    golden = _peaks([_UREA])
    f, i, fo, mz, h = _UREA
    actual = _peaks([(f, i, fo, mz * (1 + 0.05e-6), h)])
    assert compare_peaks(golden, actual) == []


def test_mz_outside_tolerance_flagged():
    """An m/z shift beyond tolerance on a matched key is reported."""
    golden = _peaks([_UREA])
    f, i, fo, mz, h = _UREA
    actual = _peaks([(f, i, fo, mz * (1 + 5e-6), h)])  # +5 ppm
    problems = compare_peaks(golden, actual, tolerances={"mz_ppm": 1.0})
    assert any("ppm" in p for p in problems)


def test_intensity_drift_flagged():
    """Intensity beyond the relative tolerance is reported."""
    golden = _peaks([_UREA])
    f, i, fo, mz, h = _UREA
    actual = _peaks([(f, i, fo, mz, h * 1.1)])  # +10%
    problems = compare_peaks(golden, actual, tolerances={"intensity_rel": 0.01})
    assert any("intensity" in p for p in problems)


def test_missing_peak_flagged():
    """A golden peak absent from the actual set is reported as missing."""
    golden = _peaks([_UREA, _BR])
    actual = _peaks([_UREA])
    problems = compare_peaks(golden, actual)
    assert any("missing peak" in p and "Br-" in p for p in problems)


def test_unexpected_peak_flagged():
    """An actual peak not present in the goldens is reported as unexpected."""
    golden = _peaks([_UREA])
    actual = _peaks([_UREA, _BR])
    problems = compare_peaks(golden, actual)
    assert any("unexpected peak" in p and "Br-" in p for p in problems)


def test_empty_actual_flags_all_missing():
    """No produced peaks is a hard failure (every golden peak is missing)."""
    golden = _peaks([_UREA, _BR])
    problems = compare_peaks(golden, _peaks([]))
    assert sum("missing peak" in p for p in problems) == 2


def test_same_isotope_different_files_are_distinct_keys():
    """The same isotope in two files are separate peaks (key includes filename)."""
    f1 = ("Orbion_neg_Br_a.raw", "iso_br_1", "Br-", 78.91839, 800.0)
    f2 = ("Orbion_neg_Br_b.raw", "iso_br_1", "Br-", 78.91839, 800.0)
    golden = _peaks([f1, f2])
    # Drop the second file's peak from actual -> exactly one missing.
    problems = compare_peaks(golden, _peaks([f1]))
    assert sum("missing peak" in p for p in problems) == 1


def test_duplicate_keys_flagged():
    """Duplicate keys make the join ambiguous and are reported."""
    golden = _peaks([_UREA, _UREA])  # same key twice
    problems = compare_peaks(golden, _peaks([_UREA]))
    assert any("duplicate key" in p for p in problems)
