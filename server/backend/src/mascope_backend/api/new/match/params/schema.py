from pydantic import BaseModel, Field, model_validator

# TODO_configuration Default Match Parameters

# global defaults
DEFAULT_MIN_ISOTOPE_ABUNDANCE = 0.1
DEFAULT_PROBABLE_MATCH_THRESHOLD = 0.8
DEFAULT_POSSIBLE_MATCH_THRESHOLD = 0.7

# tof-specific defaults
TOF_DEFAULT_MZ_TOLERANCE = 15
TOF_DEFAULT_ISOTOPE_RATIO_TOLERANCE = 0.15
TOF_DEFAULT_PEAK_MIN_INTENSITY = 0
TOF_DEFAULT_MIN_ISOTOPE_CORRELATION = 0

# Default TOF calibration parameters
MZ_ERROR_TOLERANCE = 10
TIC_THRESHOLD = 1e6

# orbi-specific defaults
ORBI_DEFAULT_MZ_TOLERANCE = 5
ORBI_DEFAULT_ISOTOPE_RATIO_TOLERANCE = 0.2
ORBI_DEFAULT_PEAK_MIN_INTENSITY = 0
ORBI_DEFAULT_MIN_ISOTOPE_CORRELATION = 0


class BaseMatchParams(BaseModel):
    # global
    min_isotope_abundance: float = Field(
        DEFAULT_MIN_ISOTOPE_ABUNDANCE,
        description="Minimum relative abundance of isotopes to consider in the match.",
    )
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
    min_isotope_correlation: float = Field(
        description="Minimum correlation of isotopic pattern required for a match.",
    )

    @model_validator(mode="after")
    @classmethod
    def validate_thresholds(cls, values):
        probable_match_threshold = values.probable_match_threshold
        possible_match_threshold = values.possible_match_threshold

        if (
            possible_match_threshold is not None
            and probable_match_threshold is not None
        ):
            if possible_match_threshold > probable_match_threshold:
                raise ValueError(
                    "Possible match threshold must be less than or equal to probable match threshold"
                )
        return values


class TofMatchParams(BaseMatchParams):
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
    min_isotope_correlation: float = Field(
        TOF_DEFAULT_MIN_ISOTOPE_CORRELATION,
        description="Minimum correlation of isotopic pattern required for a match.",
    )


class OrbiMatchParams(BaseMatchParams):
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
    min_isotope_correlation: float = Field(
        ORBI_DEFAULT_MIN_ISOTOPE_CORRELATION,
        description="Minimum correlation of isotopic pattern required for a match.",
    )


class MatchParams(BaseModel):
    tof: TofMatchParams = TofMatchParams()
    orbi: OrbiMatchParams = OrbiMatchParams()
