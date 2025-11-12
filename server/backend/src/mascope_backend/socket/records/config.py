"""Configuration for record synchronization events."""

from pydantic import BaseModel


class RecordSyncConfig(BaseModel):
    """Configuration settings for record synchronization events."""

    EVENT_ID_LENGTH: int = 12
    OPERATIONS: list[str] = ["created", "updated", "deleted", "reload"]


record_sync_config = RecordSyncConfig()
