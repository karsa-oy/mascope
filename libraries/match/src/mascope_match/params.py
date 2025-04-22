"""
Parameters and configuration for match computation.

This module defines constants and configurations used in the match computation process.
"""

from pydantic import BaseModel, Field

# tof-specific defaults
TOF_FITTING_THRESHOLD = 0.9

# orbi-specific defaults
ORBI_FITTING_THRESHOLD = 0.6

# default values for unmatched isotopes
DEFAULT_UNMATCHED_SAMPLE_PEAK_ID = -1
DEFAULT_UNMATCHED_SAMPLE_PEAK_INTENSITY = 0.0
DEFAULT_UNMATCHED_SAMPLE_PEAK_INTENSITY_RELATIVE = 0.0
DEFAULT_UNMATCHED_MATCH_ABUNDANCE_ERROR = 1.0
DEFAULT_UNMATCHED_MATCH_MZ_ERROR = 0.0
DEFAULT_UNMATCHED_MATCH_ISOTOPE_CORRELATION = 0.0
DEFAULT_UNMATCHED_MATCH_SCORE = 0.0
DEFAULT_UNMATCHED_SAMPLE_PEAK_TOF = 0.0


class UnmatchedIsotopeParams(BaseModel):
    """Default parameters for isotopes without matching peaks."""

    sample_peak_id: int = Field(
        DEFAULT_UNMATCHED_SAMPLE_PEAK_ID,
        description="ID value for isotopes without matching peaks. -1 indicates no real peak.",
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
    match_isotope_correlation: float = Field(
        DEFAULT_UNMATCHED_MATCH_ISOTOPE_CORRELATION,
        description="Default isotope correlation for isotopes without matching peaks.",
    )
    match_score: float = Field(
        DEFAULT_UNMATCHED_MATCH_SCORE,
        description="Default match score for isotopes without matching peaks. 0.0 indicates no match.",
    )
    sample_peak_tof: float = Field(
        DEFAULT_UNMATCHED_SAMPLE_PEAK_TOF,
        description="Default TOF value for isotopes without matching peaks.",
    )
