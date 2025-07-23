"""
Sample item configuration settings.

Centralized configuration for sample item rules.
"""

from pydantic import BaseModel


class SampleItemConfig(BaseModel):
    """
    Configuration settings for sample item rules.
    """

    # Default values
    DEFAULT_LOCKED_STATUS: int = 0

    # Business rules
    ACQUISITION_AUTO_LOCK: bool = (
        True  # Sample items in ACQUISITION batches are auto-locked
    )

    # Sample item type categories based on filter_id requirements
    SAMPLE_TYPES_FILTER_ID_REQUIRED: list = ["FILTER_REGENERATION", "FILTER_BACKGROUND"]
    SAMPLE_TYPES_FILTER_ID_OPTIONAL: list = [
        "BLANK",
        "SAMPLE",
        "UNKNOWN",
        "ACQUISITION",
    ]
    SAMPLE_TYPES_FILTER_ID_NOT_ALLOWED: list = ["INSTRUMENT_BACKGROUND", "ONLINE"]

    # System-only types (cannot be set by users through updates)
    SYSTEM_ONLY_SAMPLE_TYPES: list = ["ACQUISITION"]

    SAMPLE_POLARITY: list = ["+", "-"]

    # Validation patterns
    FILTER_ID_REGEX: str = (
        r"^[0-9A-Z]{6}$"  # 6 characters, uppercase letters and numbers
    )

    @property
    def all_sample_types(self) -> list:
        """Get all valid sample item types."""
        return (
            self.SAMPLE_TYPES_FILTER_ID_REQUIRED
            + self.SAMPLE_TYPES_FILTER_ID_OPTIONAL
            + self.SAMPLE_TYPES_FILTER_ID_NOT_ALLOWED
        )

    @property
    def user_editable_sample_types(self) -> list:
        """Get sample types that users can set through updates."""
        return [
            sample_type
            for sample_type in self.all_sample_types
            if sample_type not in self.SYSTEM_ONLY_SAMPLE_TYPES
        ]


# Global sample item configuration instance
sample_item_config = SampleItemConfig()
