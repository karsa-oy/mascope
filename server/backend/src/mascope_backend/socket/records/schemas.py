"""Record synchronization event schemas."""

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator
from mascope_backend.socket.records.config import record_sync_config


class RecordEvent(BaseModel):
    """
    Record synchronization event for real-time frontend updates.

    Operations:
    - created: New record added (includes full record data)
    - updated: Record modified (full or partial record data)
      - Full update: record contains all fields, changed_fields=None
      - Partial update: record contains only changed fields, changed_fields=[...]
        Frontend merges changed fields into existing record
    - deleted: Record removed (no record data, just ID)
    - reload: Bulk reload trigger (no record data, signals store to reload it's list with API call)
    """

    event_id: str = Field(
        ...,
        length=record_sync_config.EVENT_ID_LENGTH,
        description="Unique event identifier",
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    operation: Literal["created", "updated", "deleted", "reload"]
    record_type: str = Field(
        ...,
        description="Record type (matches frontend store name)",
        examples=["batch", "workspace", "target_collection"],
    )
    record_id: str | None = Field(
        None, description="Primary key of affected record (optional for reload)"
    )
    record: dict[str, Any] | None = Field(None, description="Full record data")
    changed_fields: list[str] | None = Field(
        None, description="Changed fields (updated only)"
    )

    @model_validator(mode="after")
    def validate_operation_data(self):
        """Validate data presence based on operation type."""
        # Validate operation is in config
        if self.operation not in record_sync_config.OPERATIONS:
            raise ValueError(
                f"Invalid operation: {self.operation}. Must be one of: {record_sync_config.OPERATIONS}"
            )

        # record_id required for created/updated/deleted, optional for reload
        if self.operation in ["created", "updated", "deleted"] and not self.record_id:
            raise ValueError(f"record_id required for {self.operation}")

        # record data validation
        if self.operation in ["created", "updated"] and self.record is None:
            raise ValueError(f"record required for {self.operation}")
        if self.operation in ["deleted", "reload"] and self.record is not None:
            raise ValueError(f"record must be null for {self.operation}")

        # changed_fields only for updated
        if self.operation != "updated" and self.changed_fields is not None:
            raise ValueError("changed_fields only valid for updated")

        return self

    def event_name(self) -> str:
        """Generate socket event name."""
        return f"{self.record_type}_{self.operation}"
