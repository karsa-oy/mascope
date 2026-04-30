"""Pydantic schemas for workspace and workspace membership endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from mascope_backend.api.new.auth.config import auth_settings


# Valid workspace-level roles, aligned with global role names
WORKSPACE_ROLES = list(auth_settings.ROLE_ACCESS_LEVELS.keys())


class WorkspaceRead(BaseModel):
    """Response schema for a workspace."""

    workspace_id: str
    workspace_name: str
    workspace_description: str | None = None
    workspace_status: str
    is_system: bool = False
    workspace_utc_created: datetime | None = None
    workspace_utc_modified: datetime | None = None

    model_config = {"from_attributes": True}


class WorkspaceCreate(BaseModel):
    """Request schema for creating a workspace."""

    workspace_name: str = Field(..., min_length=1, max_length=256)
    workspace_description: str | None = Field(None, max_length=4096)


class WorkspaceUpdate(BaseModel):
    """Request schema for updating a workspace."""

    workspace_name: str | None = Field(None, min_length=1, max_length=256)
    workspace_description: str | None = Field(None, max_length=4096)
    workspace_status: str | None = Field(None, pattern="^(active|archived)$")


class WorkspaceMemberRead(BaseModel):
    """Response schema for a workspace membership."""

    workspace_member_id: str
    workspace_id: str
    user_id: int
    workspace_role: str
    granted_at: datetime
    granted_by: int | None = None

    model_config = {"from_attributes": True}


class WorkspaceMemberCreate(BaseModel):
    """Request schema for adding a member to a workspace."""

    user_id: int
    workspace_role: str = Field(default="guest")

    @field_validator("workspace_role")
    @classmethod
    def validate_role(cls, v):
        if v not in WORKSPACE_ROLES:
            raise ValueError(f"workspace_role must be one of {WORKSPACE_ROLES}")
        return v


class WorkspaceMemberUpdate(BaseModel):
    """Request schema for updating a member's role."""

    workspace_role: str

    @field_validator("workspace_role")
    @classmethod
    def validate_role(cls, v):
        if v not in WORKSPACE_ROLES:
            raise ValueError(f"workspace_role must be one of {WORKSPACE_ROLES}")
        return v
