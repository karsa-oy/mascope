import pytest
from pydantic import ValidationError

from mascope_match.params import (
    ORBI_DEFAULT_ISOTOPE_ABUNDANCE_THRESHOLD,
    TOF_DEFAULT_ISOTOPE_ABUNDANCE_THRESHOLD,
    BaseMatchParams,
    OrbiMatchParams,
    TofMatchParams,
)


class TestIsotopeAbundanceThreshold:
    def test_instrument_defaults(self):
        assert (
            OrbiMatchParams().isotope_abundance_threshold
            == ORBI_DEFAULT_ISOTOPE_ABUNDANCE_THRESHOLD
            == 1e-4
        )
        assert (
            TofMatchParams().isotope_abundance_threshold
            == TOF_DEFAULT_ISOTOPE_ABUNDANCE_THRESHOLD
            == 1e-3
        )

    def test_override_is_accepted(self):
        # Strong reagent ions may opt into a lower threshold.
        params = OrbiMatchParams(isotope_abundance_threshold=1e-6)
        assert params.isotope_abundance_threshold == 1e-6

    def test_base_requires_threshold(self):
        # BaseMatchParams declares the field without a default; it must be provided.
        with pytest.raises(ValidationError):
            BaseMatchParams(
                mz_tolerance=5,
                isotope_ratio_tolerance=0.2,
                peak_min_intensity=0,
            )
