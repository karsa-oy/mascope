"""
Sample batch configuration settings.

Centralized configuration for sample batch types and rules.
"""

from pydantic import BaseModel
from mascope_backend.api.models.target.collections.config import (
    target_collection_config,
)


class SampleBatchConfig(BaseModel):
    """
    Configuration settings for sample batch types and rules.
    """

    SAMPLE_BATCH_TYPES: list = ["ACQUISITION", "ANALYSIS"]

    # Default values
    DEFAULT_SAMPLE_BATCH_TYPE: str = "ANALYSIS"
    DEFAULT_LOCKED_STATUS: int = 0

    # Polarity constraints by batch type
    ACQUISITION_POLARITY: list = ["+", "-"]
    ANALYSIS_POLARITY: str = "+-"

    # Polarity-based batch naming configuration
    ACQUISITION_POLARITY_NAMES: dict = {"+": "positive", "-": "negative"}

    # Business rules
    ACQUISITION_AUTO_LOCK: bool = True

    # Target collection constraints
    ACQUISITION_COLLECTION_TYPES: list = ["DIAGNOSTICS"]
    ANALYSIS_COLLECTION_TYPES: list = target_collection_config.TARGET_COLLECTION_TYPES

    @property
    def all_sample_batch_polarities(self) -> list:
        """Get all valid sample batch polarities."""
        return self.ACQUISITION_POLARITY + [self.ANALYSIS_POLARITY]

    def get_allowed_collection_types(self, sample_batch_type: str) -> list:
        """Get allowed collection types for a sample batch type."""
        return getattr(self, f"{sample_batch_type}_COLLECTION_TYPES", [])

    def get_acquisition_polarity_name(self, polarity: str) -> str:
        """Get batch name for acquisition polarity symbol."""
        return self.ACQUISITION_POLARITY_NAMES.get(polarity)


# Global sample batch configuration instance
sample_batch_config = SampleBatchConfig()
