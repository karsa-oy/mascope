"""
Configuration settings specific to access tokens used for service-to-service authentication.
"""

from typing import List
from pydantic import BaseModel


class AccessTokenConfig(BaseModel):
    """
    Configuration settings for access tokens.
    """

    # Allowed services for access tokens
    ALLOWED_SERVICES: List[str] = [
        "mascope_sdk",  # for Jupyter notebooks API library
        "file-converter",  # for file converter service
        "tof-agent",  # for TOF-instrument agent
    ]
    # Access token-based authentication settings for Jupyter library API access
    ACCESS_TOKEN_EXPIRATION_SECONDS: int = (
        360 * 24 * 60 * 60
    )  # Access token lifetime  - 360 days in seconds
