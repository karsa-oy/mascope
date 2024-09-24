from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class UserNotification(BaseModel):
    process_id: str = Field(
        ..., description="Unique identifier for the notification process."
    )
    parent_id: Optional[str] = Field(
        None,
        description="Identifier of the parent process if this notification is part of a larger workflow.",
    )
    type: str = Field(
        ...,
        description="Type of process, corresponds to the backend function name handling the operation.",
    )
    message: str = Field(
        ..., description="User-friendly message describing the notification context."
    )
    progress: Optional[float] = Field(
        None, description="Current progress percentage of the process, if applicable"
    )
    status: str = Field(
        ...,
        description="Current status of the process, e.g., 'success', 'error', 'pending', 'warning'",
    )
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional data payload containing additional information or results.",
    )
    error: Optional[Dict[str, Any]] = Field(
        None, description="Optional details about an error if the status is 'error'."
    )

    class Config:
        exclude_none = True  # Exclude fields with None values from output

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["success", "error", "pending", "warning"]
        if v not in valid_statuses:
            raise ValueError(
                f"Invalid status '{v}'. Valid statuses are {valid_statuses}."
            )
        return v

    @field_validator("progress")
    @classmethod
    def validate_progress(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("Progress must be between 0 and 100.")
        return v
