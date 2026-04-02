"""
Parameters and configuration for match computation.

This module defines constants, configurations, and parameter models used in match computation.
"""

from pydantic import BaseModel, Field, model_validator


# Fitting thresholds
TOF_FITTING_THRESHOLD = 0.9
ORBI_FITTING_THRESHOLD = 0.6

# Default match thresholds
DEFAULT_PROBABLE_MATCH_THRESHOLD = 0.8
DEFAULT_POSSIBLE_MATCH_THRESHOLD = 0.7

# TOF-specific defaults
TOF_DEFAULT_MZ_TOLERANCE = 15
TOF_DEFAULT_ISOTOPE_RATIO_TOLERANCE = 0.15
TOF_DEFAULT_PEAK_MIN_INTENSITY = 0

# Orbi-specific defaults
ORBI_DEFAULT_MZ_TOLERANCE = 5
ORBI_DEFAULT_ISOTOPE_RATIO_TOLERANCE = 0.2
ORBI_DEFAULT_PEAK_MIN_INTENSITY = 0

# default values for unmatched isotopes
DEFAULT_UNMATCHED_SAMPLE_PEAK_ID = ""
DEFAULT_UNMATCHED_SAMPLE_PEAK_INTENSITY = 0.0
DEFAULT_UNMATCHED_SAMPLE_PEAK_INTENSITY_RELATIVE = 0.0
DEFAULT_UNMATCHED_MATCH_ABUNDANCE_ERROR = 1.0
DEFAULT_UNMATCHED_MATCH_MZ_ERROR = 0.0
DEFAULT_UNMATCHED_MATCH_SCORE = 0.0
DEFAULT_UNMATCHED_SAMPLE_PEAK_TOF = -1.0


class BaseMatchParams(BaseModel):
    """Base class for instrument-specific match parameters."""

    # global
    possible_match_threshold: float = Field(
        DEFAULT_POSSIBLE_MATCH_THRESHOLD,
        description="Threshold score above which a match is considered possible, but below the probable match threshold.",
    )
    probable_match_threshold: float = Field(
        DEFAULT_PROBABLE_MATCH_THRESHOLD,
        description="Threshold score above which a match is considered probable.",
    )
    # instrument
    mz_tolerance: int = Field(
        description="Tolerance for mass-to-charge ratio (m/z) error.",
    )
    isotope_ratio_tolerance: float = Field(
        description="Tolerance for the ratio of isotopic abundances.",
    )
    peak_min_intensity: float = Field(
        description="Minimum peak intensity threshold for considering a match.",
    )

    @model_validator(mode="after")
    def validate_thresholds(self):
        if (
            self.possible_match_threshold is not None
            and self.probable_match_threshold is not None
            and self.possible_match_threshold > self.probable_match_threshold
        ):
            raise ValueError(
                "Possible match threshold must be less than or equal to probable match threshold"
            )
        return self


class TofMatchParams(BaseMatchParams):
    """TOF instrument match parameters."""

    mz_tolerance: int = Field(
        TOF_DEFAULT_MZ_TOLERANCE,
        description="Tolerance for mass-to-charge ratio (m/z) error.",
    )
    isotope_ratio_tolerance: float = Field(
        TOF_DEFAULT_ISOTOPE_RATIO_TOLERANCE,
        description="Tolerance for the ratio of isotopic abundances.",
    )
    peak_min_intensity: float = Field(
        TOF_DEFAULT_PEAK_MIN_INTENSITY,
        description="Minimum peak intensity threshold for considering a match.",
    )


class OrbiMatchParams(BaseMatchParams):
    """Orbitrap instrument match parameters."""

    mz_tolerance: int = Field(
        ORBI_DEFAULT_MZ_TOLERANCE,
        description="Tolerance for mass-to-charge ratio (m/z) error.",
    )
    isotope_ratio_tolerance: float = Field(
        ORBI_DEFAULT_ISOTOPE_RATIO_TOLERANCE,
        description="Tolerance for the ratio of isotopic abundances.",
    )
    peak_min_intensity: float = Field(
        ORBI_DEFAULT_PEAK_MIN_INTENSITY,
        description="Minimum peak intensity threshold for considering a match.",
    )


class MatchParams(BaseModel):
    """Container for all instrument-specific match parameters."""

    tof: TofMatchParams = TofMatchParams()
    orbi: OrbiMatchParams = OrbiMatchParams()


class UnmatchedIsotopeParams(BaseModel):
    """Default parameters for isotopes without matching peaks."""

    sample_peak_id: str = Field(
        DEFAULT_UNMATCHED_SAMPLE_PEAK_ID,
        description="ID value for isotopes without matching peaks. Empty string indicates no real peak.",
    )
    sample_peak_intensity: float = Field(
        DEFAULT_UNMATCHED_SAMPLE_PEAK_INTENSITY,
        description="Default peak intensity for isotopes without matching peaks.",
    )
    sample_peak_intensity_relative: float = Field(
        DEFAULT_UNMATCHED_SAMPLE_PEAK_INTENSITY_RELATIVE,
        description="Default relative peak intensity for isotopes without matching peaks.",
    )
    match_abundance_error: float = Field(
        DEFAULT_UNMATCHED_MATCH_ABUNDANCE_ERROR,
        description="Default abundance error for isotopes without matching peaks. 1.0 indicates maximum error.",
    )
    match_mz_error: float = Field(
        DEFAULT_UNMATCHED_MATCH_MZ_ERROR,
        description="Default m/z error for isotopes without matching peaks.",
    )
    match_score: float = Field(
        DEFAULT_UNMATCHED_MATCH_SCORE,
        description="Default match score for isotopes without matching peaks. 0.0 indicates no match.",
    )
    sample_peak_tof: float = Field(
        DEFAULT_UNMATCHED_SAMPLE_PEAK_TOF,
        description="Default TOF value for isotopes without matching peaks.",
    )


unmatched_isotope_params = UnmatchedIsotopeParams()
