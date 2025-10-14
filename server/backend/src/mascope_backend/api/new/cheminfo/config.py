"""
Configuration settings for ChemInfo API integration.
"""

from pydantic import BaseModel


class ChemInfoConfig(BaseModel):
    """
    Configuration settings for the ChemInfo API integration.
    """

    # Base URL for the ChemInfo API
    BASE_URL: str = "https://info.cheminfo.org"

    # Timeout in seconds for HTTP requests to ChemInfo API
    REQUEST_TIMEOUT: float = 10.0

    # Default precision for m/z matching in ppm
    DEFAULT_MZ_PRECISION: float = 10.0

    # Default formula range for queries
    DEFAULT_FORMULA_RANGE: str = "C0-100 H0-100 O0-100 N0-100"

    # Debounce delay in milliseconds for frontend API requests
    DEBOUNCE_DELAY_MS: int = 800


# Global config instance for ChemInfo integration
cheminfo_config = ChemInfoConfig()
