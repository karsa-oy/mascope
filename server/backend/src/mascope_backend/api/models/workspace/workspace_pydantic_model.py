from pydantic import BaseModel, Field, field_validator, ConfigDict
from mascope_backend.api.models.base_pydantic_model import QueryParamsModel
from datetime import datetime


class WorkspaceValidator:
    """Mixin class with common validators."""

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


class WorkspaceBase(WorkspaceValidator, BaseModel):
    """Base model with common fields for Workspace."""

    workspace_name: str = Field(..., description="Name of the workspace")
    workspace_description: str | None = Field(
        None, description="Description of the workspace"
    )
    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(WorkspaceBase):
    """Model used for workspace creation requests."""

    pass


class WorkspaceRead(WorkspaceBase):
    """Model used for reading workspaces, includes all database fields."""

    workspace_id: str = Field(..., description="Unique identifier for the workspace")
    workspace_utc_created: datetime = Field(
        ..., description="Timestamp when workspace was created"
    )
    workspace_utc_modified: datetime | None = Field(
        None, description="Timestamp when workspace was last modified"
    )


class WorkspaceUpdate(WorkspaceValidator, BaseModel):
    """Model used for workspace update requests - all fields optional."""

    workspace_name: str | None = Field(None, description="Name of the workspace")
    workspace_description: str | None = Field(
        None, description="Description of the workspace"
    )

    model_config = ConfigDict(from_attributes=True)


class GetWorkspacesQueryParams(QueryParamsModel):
    """
    Query parameters for filtering and paginating workspace listings.

    This model defines the parameters that can be passed to the get_workspaces endpoint
    to control sorting, ordering, and pagination of workspace results.
    """

    sort: str | None = Field(
        "workspace_utc_created",
        description="Column name by which you want to sort the results. The column name should be one of the columns in the workspace table.",
    )
    order: str | None = Field(
        "asc",
        description="Sorting order which can be asc for ascending or desc for descending.",
    )
    page: int = Field(0, description="Page number for pagination.")
    limit: int = Field(10000, description="Number of results per page.")
