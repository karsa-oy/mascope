"""
Workspace pydantic models for API validation and serialization.

Defines data models for workspace related requests and responses
with validation rules and business logic constraints.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from mascope_backend.api.models.base_pydantic_model import QueryParamsModel
from mascope_backend.api.models.workspace.config import workspace_config


class WorkspaceIcon(BaseModel):
    """Icon configuration for workspace."""

    icon_id: str = Field(..., description="Icon identifier/class name")
    color: str = Field(..., description="Color in hex format (e.g., #3B82F6)")

    @field_validator("color")
    @classmethod
    def validate_color_format(cls, color: str) -> str:
        """Validate color is in hex format."""
        if not color.startswith("#") or len(color) != 7:
            raise ValueError("Color must be in hex format (e.g., #3B82F6)")
        return color


class WorkspaceBaseValidator:
    """Mixin class with common schemas fields validators."""

    @field_validator("workspace_name")
    @classmethod
    def validate_workspace_name(cls, workspace_name: str | None) -> str | None:
        """
        Validates that `workspace_name` is not an empty string or just whitespace.

        :param workspace_name: The name provided for the workspace.
        :raises ValueError: If the workspace_name is an empty string or contains only whitespace.
        :return: The workspace_name if it is valid.
        """
        if workspace_name is not None and workspace_name.strip() == "":
            raise ValueError(
                "The workspace name cannot be empty or contain only whitespace."
            )
        return workspace_name


class WorkspaceValidator(WorkspaceBaseValidator):
    """Validators for all fields."""

    @field_validator("workspace_type")
    @classmethod
    def validate_workspace_type(cls, workspace_type: str | None) -> str | None:
        """Validate workspace type."""
        if workspace_type and workspace_type not in workspace_config.WORKSPACE_TYPES:
            raise ValueError(
                f"Invalid workspace type. Must be one of: {workspace_config.WORKSPACE_TYPES}"
            )
        return workspace_type

    @field_validator("instrument")
    @classmethod
    def validate_instrument(cls, instrument: str | None) -> str | None:
        """Validate instrument is not empty."""
        if instrument is not None and instrument.strip() == "":
            raise ValueError("Instrument cannot be empty or contain only whitespace")
        return instrument


class WorkspaceBase(WorkspaceValidator, BaseModel):
    """Base model with common fields for Workspace."""

    workspace_name: str = Field(..., description="Name of the workspace")
    workspace_description: str | None = Field(
        None, description="Description of the workspace"
    )
    workspace_type: str = Field(
        default=workspace_config.DEFAULT_WORKSPACE_TYPE,
        description="Type of workspace (ACQUISITION or ANALYSIS)",
    )
    instrument: str | None = Field(
        None, description="Instrument associated with the workspace"
    )
    icon: WorkspaceIcon | None = Field(
        None, description="Icon configuration with icon_id and color"
    )

    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(WorkspaceBase):
    """Model used for workspace creation requests."""

    @model_validator(mode="after")
    def validate_acquisition_constraints(self):
        """Validate rules for ACQUISITION workspaces."""
        if self.workspace_type == "ACQUISITION":
            # ACQUISITION workspaces must have instrument
            if not self.instrument:
                raise ValueError("Acquisition workspaces must specify an instrument")

            # Validate name ends with instrument (case-insensitive)
            if not self.workspace_name.lower().endswith(self.instrument.lower()):
                raise ValueError(
                    f"Acquisition workspace name should end with the instrument name. "
                    f"Suggested: '{workspace_config.ACQUISITION_NAME_PREFIX} {self.instrument}'"
                )

        return self


class WorkspaceRead(WorkspaceBase):
    """Model used for reading workspaces, includes database fields."""

    workspace_id: str = Field(..., description="Unique identifier for the workspace")
    locked: int = Field(
        description="Lock status of the workspace (0=unlocked, 1=locked)",
    )
    workspace_utc_created: datetime = Field(
        ..., description="Timestamp when workspace was created"
    )
    workspace_utc_modified: datetime | None = Field(
        None, description="Timestamp when workspace was last modified"
    )


class WorkspaceUpdate(WorkspaceBaseValidator, BaseModel):
    """Model used for workspace update requests - only user-editable fields, all fields optional."""

    workspace_name: str | None = Field(None, description="Name of the workspace")
    workspace_description: str | None = Field(
        None, description="Description of the workspace"
    )
    icon: WorkspaceIcon | None = Field(
        None, description="Icon configuration with icon_id and color"
    )

    model_config = ConfigDict(from_attributes=True)


class GetWorkspacesQueryParams(WorkspaceBaseValidator, QueryParamsModel):
    """
    Query parameters for filtering and paginating workspace listings.

    This model defines the parameters that can be passed to the get_workspaces endpoint
    to control sorting, ordering, and pagination of workspace results.
    """

    workspace_name: str | None = Field(
        None,
        description="Filter by workspace name.",
    )
    workspace_type: list[str] | None = Field(
        default=None,
        description="Filter by workspace types (ACQUISITION, ANALYSIS). Can specify multiple types.",
    )
    instrument: list[str] | None = Field(
        None,
        description="Filter by instrument associated with the workspace.  Can specify multiple instruments.",
    )
    sort: str | None = Field(
        "workspace_utc_created",
        description="Column name by which you want to sort the results. The column name should be one of the columns in the workspace table.",
    )
    order: str | None = Field(
        "asc",
        description="Sorting order which can be asc for ascending or desc for descending.",
    )
    page: int | None = Field(None, description="Page number for pagination.")
    limit: int | None = Field(None, description="Number of results per page.")

    @field_validator("workspace_type")
    @classmethod
    def validate_workspace_type_list(
        cls, workspace_types: list[str] | None
    ) -> list[str] | None:
        """Validate workspace types in the list."""
        if workspace_types:
            for workspace_type in workspace_types:
                if workspace_type not in workspace_config.WORKSPACE_TYPES:
                    raise ValueError(
                        f"Invalid workspace type '{workspace_type}'. Must be one of: {workspace_config.WORKSPACE_TYPES}"
                    )
        return workspace_types
