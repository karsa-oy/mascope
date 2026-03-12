"""Unit tests for calibration matching and summary statistics methods."""

import numpy as np
import pandas as pd
from conftest import get_test_calibration_handler


def _make_isotope_row(mz):
    return pd.Series(
        {
            "mz": mz,
            "sample_peak_mz": np.nan,
            "sample_peak_tof": np.nan,
            "sample_peak_intensity": np.nan,
            "matched_peak_idx": np.nan,
        }
    )


class TestMatchMaxInRange:
    """Tests for _match_max_in_range.

    Handler refine_window (Orbi default after with_defaults) = 10 ppm.
    At target_mz = 100, tolerance = 0.001.

    Expected behaviors:
    - If a single peak is within the refine window, it should be matched.
    - If multiple peaks are within the refine window, the one with the highest intensity wins.
    - If no peaks are within the refine window, the row should be unchanged (NaN values remain).
    - If a peak is exactly on the boundary of the refine window, it should be matched.
    """

    def setup_method(self):
        self.orbi_pos_handler = get_test_calibration_handler("orbitrap", "+")
        self.isotope_row = _make_isotope_row(100.0)

    def test_single_peak_in_range_matched(self):
        peaks = {
            "mz": np.array([100.0005]),
            "tof": np.array([5000.0]),
            "intensity": np.array([42.0]),
        }
        isotope_row = self.orbi_pos_handler._match_max_in_range(self.isotope_row, peaks)

        assert isotope_row["sample_peak_mz"] == 100.0005
        assert isotope_row["sample_peak_tof"] == 5000.0
        assert isotope_row["sample_peak_intensity"] == 42.0

    def test_highest_intensity_wins(self):
        peaks = {
            "mz": np.array([100.0002, 100.0005, 100.0008]),
            "tof": np.array([4998.0, 5000.0, 5002.0]),
            "intensity": np.array([10.0, 99.0, 50.0]),
        }
        isotope_row = self.orbi_pos_handler._match_max_in_range(self.isotope_row, peaks)

        assert isotope_row["sample_peak_mz"] == 100.0005
        assert isotope_row["sample_peak_intensity"] == 99.0

    def test_no_peaks_in_range_row_unchanged(self):
        peaks = {
            "mz": np.array([200.0]),
            "tof": np.array([8000.0]),
            "intensity": np.array([50.0]),
        }
        isotope_row = self.orbi_pos_handler._match_max_in_range(self.isotope_row, peaks)

        assert np.isnan(isotope_row["sample_peak_mz"])
        assert np.isnan(isotope_row["sample_peak_intensity"])

    def test_peak_at_exact_boundary(self):
        target_mz = 100.0
        boundary_mz = (
            target_mz + target_mz * self.orbi_pos_handler.params.refine_window * 1e-6
        )
        peaks = {
            "mz": np.array([boundary_mz]),
            "tof": np.array([5000.0]),
            "intensity": np.array([7.0]),
        }
        isotope_row = self.orbi_pos_handler._match_max_in_range(self.isotope_row, peaks)

        np.testing.assert_allclose(isotope_row["sample_peak_mz"], boundary_mz)


class TestRemoveOutliers:
    """Tests for _remove_outliers.

    Uses median absolute deviation (MAD): outlier when |error - median| > 3 * MAD.

    Expected behaviors:
    - If no outliers are present, all rows are kept.
    - If a clear outlier is present, it is removed.
    - If only one row is present, it is kept (since we can't define outliers with a single point).
    """

    def setup_method(self):
        self.orbi_pos_handler = get_test_calibration_handler("orbitrap", "+")
        self.isotope_row = _make_isotope_row(100.0)

    def test_no_outliers(self):
        df = pd.DataFrame({"calibration_mz_error": [1.0, 1.1, 0.9, 1.05]})
        result = self.orbi_pos_handler._remove_outliers(df)

        assert len(result) == 4

    def test_clear_outlier_removed(self):
        errors = [1.0, 1.1, 0.9, 1.05, 50.0]
        df = pd.DataFrame({"calibration_mz_error": errors})

        result = self.orbi_pos_handler._remove_outliers(df)

        assert 50.0 not in result["calibration_mz_error"].values
        assert len(result) == 4

    def test_single_row_kept(self):
        df = pd.DataFrame({"calibration_mz_error": [5.0]})

        result = self.orbi_pos_handler._remove_outliers(df)

        assert len(result) == 1


class TestGetSummaryRow:
    """Tests for _get_summary_row.

    Expected behaviors:
    - The summary row contains the mean absolute match_mz_error and calibration_mz_error.
    - The summary row contains the absolute difference between these two means as mz_error_diff.
    - The summary row contains the sum of calibrant_to_tic.
    - The summary row is correctly calculated even if only one row is present.
    """

    def setup_method(self):
        self.orbi_pos_handler = get_test_calibration_handler("orbitrap", "+")
        self.isotope_row = _make_isotope_row(100.0)

    def test_known_values(self):
        df = pd.DataFrame(
            {
                "match_mz_error": [-2.0, 4.0],
                "calibration_mz_error": [1.0, -3.0],
                "calibrant_to_tic": [0.1, 0.2],
            }
        )
        result = self.orbi_pos_handler._get_summary_row(df)

        # abs(match_mz_error).mean() = (2+4)/2 = 3.0
        assert result["match_mz_error"] == 3.0
        # abs(calibration_mz_error).mean() = (1+3)/2 = 2.0
        assert result["calibration_mz_error"] == 2.0
        # |3.0 - 2.0| = 1.0
        assert result["mz_error_diff"] == 1.0
        # 0.1 + 0.2 = 0.3
        np.testing.assert_almost_equal(result["calibrant_to_tic"], 0.3)

    def test_single_row(self):
        df = pd.DataFrame(
            {
                "match_mz_error": [5.0],
                "calibration_mz_error": [-3.0],
                "calibrant_to_tic": [0.05],
            }
        )
        result = self.orbi_pos_handler._get_summary_row(df)

        assert result["match_mz_error"] == 5.0
        assert result["calibration_mz_error"] == 3.0
        assert result["calibrant_to_tic"] == 0.05
