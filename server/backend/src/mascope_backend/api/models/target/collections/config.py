"""
Target collection configuration settings.
"""

from pydantic import BaseModel


class TargetCollectionConfig(BaseModel):
    """
    Configuration settings for target collection types and constraints.
    """

    # Collection types
    TARGET_COLLECTION_TYPES: list = ["TARGETS", "DIAGNOSTICS", "CALIBRANTS"]

    # Default collection type
    DEFAULT_TARGET_COLLECTION_TYPE: str = "TARGETS"

    # Collection type constraints for sample batches
    TARGETS_BATCH_TYPES: list = ["ANALYSIS"]
    DIAGNOSTICS_BATCH_TYPES: list = ["ACQUISITION", "ANALYSIS"]
    CALIBRANTS_BATCH_TYPES: list = ["ANALYSIS"]

    # Compound limits by collection type
    DIAGNOSTICS_MAX_COMPOUNDS: int = 10

    def get_allowed_batch_types(self, target_collection_type: str) -> list:
        """Get allowed batch types for a target collection type."""
        return getattr(self, f"{target_collection_type}_BATCH_TYPES", [])


# Global target collection configuration instance
target_collection_config = TargetCollectionConfig()
