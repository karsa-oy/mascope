"""
Ionization mechanism configuration settings.

Centralized configuration for ionization mechanism types and defaults.
"""

from pydantic import BaseModel


class IonizationMechanismConfig(BaseModel):
    """
    Configuration settings for ionization mechanisms.
    """

    # Polarity constraints
    IONIZATION_MECHANISM_POLARITY: list = ["+", "-"]


# Global ionization mechanism configuration instance
ionization_mechanism_config = IonizationMechanismConfig()
