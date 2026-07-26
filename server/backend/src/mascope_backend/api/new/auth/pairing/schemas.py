import re

from pydantic import BaseModel, Field, field_validator

from mascope_backend.api.new.auth.pairing.config import pairing_settings


class PairingStartRequest(BaseModel):
    """Request body for an agent starting a pairing."""

    service_name: str = Field(
        ...,
        description="The agent service requesting a token (e.g. 'file-agent').",
    )
    machine_name: str | None = Field(
        None,
        max_length=64,
        description="Optional hostname of the machine being paired, shown to "
        "the approving user and stamped on the token.",
    )

    @field_validator("service_name")
    @classmethod
    def validate_service_name(cls, service_name: str) -> str:
        """Only agent services may pair."""
        if service_name not in pairing_settings.ALLOWED_SERVICES:
            raise ValueError(f"Service '{service_name}' cannot be paired.")
        return service_name

    @field_validator("machine_name")
    @classmethod
    def sanitize_machine_name(cls, machine_name: str | None) -> str | None:
        """Strip control characters; the value is displayed to the approver."""
        if machine_name is None:
            return None
        cleaned = re.sub(r"[\x00-\x1f\x7f]", "", machine_name).strip()
        return cleaned or None


class PairingApproveRequest(BaseModel):
    """Request body for a user approving a pairing code in the web app."""

    user_code: str = Field(..., max_length=16)

    @field_validator("user_code")
    @classmethod
    def normalize_user_code(cls, user_code: str) -> str:
        """Accept the code case-insensitively, with or without the dash."""
        return re.sub(r"[^A-Z0-9]", "", user_code.upper())


class PairingPollRequest(BaseModel):
    """Request body for an agent polling its pairing status."""

    device_code: str = Field(..., min_length=16, max_length=128)
