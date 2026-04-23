"""
Dataset configuration settings.

Centralized configuration for dataset types and rules.
"""

from pydantic import BaseModel


class DatasetConfig(BaseModel):
    """
    Configuration settings for dataset types and rules.
    """

    DATASET_TYPES: list = ["ACQUISITION", "ANALYSIS"]

    # Default values
    DEFAULT_DATASET_TYPE: str = "ANALYSIS"
    DEFAULT_LOCKED_STATUS: int = 0

    # Additional configurable rules
    ACQUISITION_AUTO_LOCK: bool = True

    # Naming conventions
    ACQUISITION_NAME_PREFIX: str = "Acquisitions"


# Global dataset configuration instance
dataset_config = DatasetConfig()
