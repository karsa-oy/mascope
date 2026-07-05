"""
Tests for the isotope-to-peak assignment algorithm (``_match_assign``).

The assignment rules under test (from the function's contract):

- Each isotope gets the candidate peak closest in m/z within
  ``MATCH_WINDOW_AMU``, ties broken toward the lower-m/z peak.
- Sample peaks are unique within an ion; different ions may share a peak.
- When isotopes of the same ion compete, higher relative abundance wins.
- Within an ion, assigned peak m/z ordering must follow target m/z ordering.
- With no suitable peak, the isotope stays unmatched.

All tests build the inputs directly: a target DataFrame initialized the same
way ``compute_match_isotopes`` does, and a parsed-peaks dict as produced by
``_parse_and_filter_peaks``.
"""

import numpy as np
import pandas as pd

from mascope_match.compute.isotopes import MATCH_WINDOW_AMU, _match_assign


def make_targets(rows: list[dict]) -> pd.DataFrame:
    """
    Build a target-isotope DataFrame with the placeholder columns
    ``compute_match_isotopes`` initializes before calling ``_match_assign``.

    Each row dict needs: ``mz``, ``relative_abundance``, ``target_ion_id``.
    """
    df = pd.DataFrame(rows).assign(
        sample_peak_id=np.nan,
        sample_peak_mz=np.nan,
        sample_peak_intensity=np.nan,
        sample_peak_tof=np.nan,
    )
    df["sample_peak_id"] = df["sample_peak_id"].astype("object")
    return df


def make_peaks(mzs: list[float], intensities: list[float] | None = None) -> dict:
    """Build a parsed-peaks dict as produced by ``_parse_and_filter_peaks``."""
    n = len(mzs)
    intensities = intensities if intensities is not None else [100.0] * n
    return {
        "peak_mzs": np.asarray(mzs, dtype=float),
        "peak_ids": np.asarray([f"peak_{i}" for i in range(n)], dtype=object),
        "peak_tofs": np.asarray([float(i) for i in range(n)]),
        "peak_intensities": np.asarray(intensities, dtype=float),
        "non_zero_mask": np.ones(n, dtype=bool),
    }


class TestMatchAssign:
    def test_assigns_closest_peak_within_window(self):
        targets = make_targets(
            [{"mz": 100.0, "relative_abundance": 1.0, "target_ion_id": "ion_1"}]
        )
        peaks = make_peaks([99.8, 100.02, 100.3], intensities=[5.0, 7.0, 9.0])

        result = _match_assign(targets, peaks)

        assert result.loc[0, "sample_peak_mz"] == 100.02
        assert result.loc[0, "sample_peak_id"] == "peak_1"
        assert result.loc[0, "sample_peak_intensity"] == 7.0
        assert result.loc[0, "matched_peak_idx"] == 1

    def test_no_peak_within_window_stays_unmatched(self):
        targets = make_targets(
            [{"mz": 100.0, "relative_abundance": 1.0, "target_ion_id": "ion_1"}]
        )
        # Closest peak is just outside the +-0.5 Da window.
        peaks = make_peaks([100.0 + MATCH_WINDOW_AMU + 0.01])

        result = _match_assign(targets, peaks)

        assert pd.isna(result.loc[0, "sample_peak_mz"])
        assert pd.isna(result.loc[0, "matched_peak_idx"])

    def test_equal_distance_tie_breaks_to_lower_mz(self):
        targets = make_targets(
            [{"mz": 100.0, "relative_abundance": 1.0, "target_ion_id": "ion_1"}]
        )
        peaks = make_peaks([99.9, 100.1])

        result = _match_assign(targets, peaks)

        assert result.loc[0, "sample_peak_mz"] == 99.9

    def test_higher_abundance_isotope_wins_shared_peak(self):
        # Both isotopes of the same ion want the peak at 100.0; the main
        # isotope (higher relative abundance) must get it, the minor one
        # falls back to the next candidate.
        targets = make_targets(
            [
                {"mz": 100.0, "relative_abundance": 0.2, "target_ion_id": "ion_1"},
                {"mz": 100.1, "relative_abundance": 1.0, "target_ion_id": "ion_1"},
            ]
        )
        peaks = make_peaks([100.05, 99.9])

        result = _match_assign(targets, peaks)

        # Main isotope (row 1) takes the closest peak 100.05; the minor
        # isotope takes 99.9 (which also respects m/z ordering).
        assert result.loc[1, "sample_peak_mz"] == 100.05
        assert result.loc[0, "sample_peak_mz"] == 99.9

    def test_peak_not_shared_within_ion(self):
        # One peak, two isotopes of the same ion: only the higher-abundance
        # isotope is matched.
        targets = make_targets(
            [
                {"mz": 100.0, "relative_abundance": 1.0, "target_ion_id": "ion_1"},
                {"mz": 100.1, "relative_abundance": 0.5, "target_ion_id": "ion_1"},
            ]
        )
        peaks = make_peaks([100.04])

        result = _match_assign(targets, peaks)

        assert result.loc[0, "sample_peak_mz"] == 100.04
        assert pd.isna(result.loc[1, "sample_peak_mz"])

    def test_peak_shared_across_different_ions(self):
        targets = make_targets(
            [
                {"mz": 100.0, "relative_abundance": 1.0, "target_ion_id": "ion_1"},
                {"mz": 100.01, "relative_abundance": 1.0, "target_ion_id": "ion_2"},
            ]
        )
        peaks = make_peaks([100.0])

        result = _match_assign(targets, peaks)

        assert result.loc[0, "sample_peak_mz"] == 100.0
        assert result.loc[1, "sample_peak_mz"] == 100.0

    def test_mz_ordering_enforced_within_ion(self):
        # The main isotope sits at higher target m/z and is assigned first
        # (abundance priority) to the peak at 100.12. The minor isotope's only
        # remaining candidate (100.2) lies ABOVE the main isotope's peak while
        # its target m/z lies BELOW - accepting it would invert the ion's m/z
        # ordering, so the minor isotope must stay unmatched.
        targets = make_targets(
            [
                {"mz": 100.0, "relative_abundance": 0.5, "target_ion_id": "ion_1"},
                {"mz": 100.1, "relative_abundance": 1.0, "target_ion_id": "ion_1"},
            ]
        )
        peaks = make_peaks([100.12, 100.2])

        result = _match_assign(targets, peaks)

        assert result.loc[1, "sample_peak_mz"] == 100.12
        assert pd.isna(result.loc[0, "sample_peak_mz"])

    def test_no_peaks_at_all(self):
        targets = make_targets(
            [{"mz": 100.0, "relative_abundance": 1.0, "target_ion_id": "ion_1"}]
        )
        peaks = make_peaks([])

        result = _match_assign(targets, peaks)

        assert pd.isna(result.loc[0, "sample_peak_mz"])
        assert pd.isna(result.loc[0, "matched_peak_idx"])
