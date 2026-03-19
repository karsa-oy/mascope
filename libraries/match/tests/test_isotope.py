import numpy as np
import pandas as pd

from mascope_match.compute.isotopes import calculate_match_stats


class TestCalculateMatchStats:
    def test_non_finite_ratios_are_replaced_with_zero(self):
        match_isotope_df = pd.DataFrame(
            {
                "target_ion_id": ["ion_1", "ion_1", "ion_1"],
                "relative_abundance": [1.0, 0.5, 0.1],
                "sample_peak_intensity": [0.0, 10.0, -10.0],
                "mz": [100.0, 101.0, 102.0],
                "sample_peak_mz": [100.0, 101.0, 102.0],
            }
        )

        result = calculate_match_stats(match_isotope_df)

        np.testing.assert_allclose(
            result["sample_peak_intensity_relative"].to_numpy(),
            np.array([0.0, 0.0, 0.0]),
        )
        assert np.isfinite(result["sample_peak_intensity_relative"]).all()

    def test_ratios_are_preserved(self):
        match_isotope_df = pd.DataFrame(
            {
                "target_ion_id": ["ion_1", "ion_1"],
                "relative_abundance": [1.0, 0.5],
                "sample_peak_intensity": [20.0, 10.0],
                "mz": [100.0, 101.0],
                "sample_peak_mz": [100.0, 101.0],
            }
        )

        result = calculate_match_stats(match_isotope_df)

        np.testing.assert_allclose(
            result["sample_peak_intensity_relative"].to_numpy(),
            np.array([1.0, 0.5]),
        )

    def test_existing_reference_overrides_matching_ions_only(self):
        match_isotope_df = pd.DataFrame(
            {
                "target_ion_id": ["ion_1", "ion_1", "ion_2", "ion_2"],
                "relative_abundance": [1.0, 0.5, 1.0, 0.5],
                "sample_peak_intensity": [100.0, 50.0, 20.0, 10.0],
                "mz": [100.0, 101.0, 200.0, 201.0],
                "sample_peak_mz": [100.0, 101.0, 200.0, 201.0],
            }
        )
        existing_reference_df = pd.DataFrame(
            {
                "target_ion_id": ["ion_1"],
                "sample_peak_intensity": [0.0],
                "relative_abundance": [1.0],
            }
        )

        result = calculate_match_stats(match_isotope_df, existing_reference_df)

        np.testing.assert_allclose(
            result["sample_peak_intensity_relative"].to_numpy(),
            np.array([0.0, 0.0, 1.0, 0.5]),
        )
