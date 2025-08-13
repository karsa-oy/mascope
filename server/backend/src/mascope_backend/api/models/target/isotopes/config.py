"""
Target isotope configuration settings.

Centralized configuration for target isotope types and rules.
"""

from pydantic import BaseModel


class TargetIsotopeConfig(BaseModel):
    """
    Configuration settings for target isotope types and rules.
    """

    ISOTOPE_RESOLUTION_TYPES: list[str] = ["HIGH", "LOW"]

    # Abundance constraints
    MIN_RELATIVE_ABUNDANCE: float = 0.0
    MAX_RELATIVE_ABUNDANCE: float = 1.0


target_isotope_config = TargetIsotopeConfig()
