"""
Workspace configuration settings.

Centralized configuration for workspace types and rules.
"""

from pydantic import BaseModel


class WorkspaceConfig(BaseModel):
    """
    Configuration settings for workspace types and rules.
    """

    WORKSPACE_TYPES: list = ["ACQUISITION", "ANALYSIS"]

    # Default values
    DEFAULT_WORKSPACE_TYPE: str = "ANALYSIS"
    DEFAULT_LOCKED_STATUS: int = 0

    # Additional configurable rules
    ACQUISITION_AUTO_LOCK: bool = True

    # Naming conventions
    ACQUISITION_NAME_PREFIX: str = "Acquisitions"


# Global workspace configuration instance
workspace_config = WorkspaceConfig()
