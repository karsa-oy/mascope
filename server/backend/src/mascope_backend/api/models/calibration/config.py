"""
Calibration configuration settings.

Centralized configuration for calibration parameters and rules.
"""

from pydantic import BaseModel


class CalibrationConfig(BaseModel):
    """
    Configuration settings for calibration parameters and rules.
    """

    DEFAULT_MATCH_SCORE_MIN: float = 0.0
    DEFAULT_PEAK_INTENSITY_MIN: float = 0.0
    DEFAULT_ISOTOPE_ABUNDANCE_MIN: float = 0.15

    # TOF calibration parameters
    TOF_MZ_ERROR_TOLERANCE: int = 15  # in ppm
    TOF_DEFAULT_REFINE_WINDOW: int = 100

    # Orbi calibration parameters
    ORBI_MZ_ERROR_TOLERANCE: int = 5  # in ppm
    ORBI_DEFAULT_REFINE_WINDOW: int = 10


# Global calibration configuration instance
calibration_config = CalibrationConfig()
