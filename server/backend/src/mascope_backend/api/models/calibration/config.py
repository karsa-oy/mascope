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
    DEFAULT_REFINE_WINDOW: int = 100
    DEFAULT_PEAK_INTENSITY_MIN: float = 1000.0
    DEFAULT_ISOTOPE_ABUNDANCE_MIN: float = 0.1

    # TOF calibration parameters
    MZ_ERROR_TOLERANCE: int = 10
    TIC_THRESHOLD: float = 1e6


# Global calibration configuration instance
calibration_config = CalibrationConfig()
