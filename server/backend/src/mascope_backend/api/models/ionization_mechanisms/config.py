"""
Ionization mechanism configuration settings.

Centralized configuration for ionization mechanism types and defaults.
"""

from pydantic import BaseModel


class IonizationMechanismConfig(BaseModel):
    """
    Configuration settings for ionization mechanisms.
    """

    # Default values
    DEFAULT_IS_DEFAULT_STATUS: int = 0

    # Default acquisition ionization mechanisms
    DEFAULT_ACQUISITION_MECHANISMS: list = [
        "-H-",
        "+Br-",
        "+H+",
        "+(CH4N2O)H+",
        "+CH4N2OH+",
    ]

    # Polarity constraints
    IONIZATION_MECHANISM_POLARITY: list = ["+", "-"]

    def get_default_mechanisms_by_polarity(self, polarity: str) -> list:
        """Get default mechanisms filtered by polarity."""
        return [
            mechanism
            for mechanism in self.DEFAULT_ACQUISITION_MECHANISMS
            if mechanism.endswith(polarity)
        ]


# Global ionization mechanism configuration instance
ionization_mechanism_config = IonizationMechanismConfig()
