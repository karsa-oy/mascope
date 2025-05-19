from pydantic import BaseModel, Field, field_validator, ConfigDict


class UserNotification(BaseModel):
    process_id: str = Field(
        ..., description="Unique identifier for the notification process."
    )
    parent_id: str | None = Field(
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
    progress: float | None = Field(
        None, description="Current progress percentage of the process, if applicable"
    )
    status: str = Field(
        ...,
        description="Current status of the process, e.g., 'success', 'error', 'pending', 'warning'",
    )
    data: dict[str, object] | None = Field(
        None,
        description="Optional data payload containing additional information or results.",
    )
    error: dict[str, object] | None = Field(
        None, description="Optional details about an error if the status is 'error'."
    )

    model_config = ConfigDict(exclude_none=True)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["success", "info", "error", "pending", "warning"]
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
