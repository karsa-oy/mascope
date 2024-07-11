from pydantic import BaseModel, Field
from typing import Optional


class WorkspaceBase(BaseModel):
    workspace_name: str = Field(..., description="Name of the workspace")
    workspace_description: Optional[str] = Field(
        None, description="Description of the workspace"
    )


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(WorkspaceBase):
    workspace_name: Optional[str] = Field(None, description="Name of the workspace")


class GetWorkspacesQueryParams(BaseModel):
    sort: Optional[str] = Field(
        "workspace_utc_created",
        description="Column name by which you want to sort the results. The column name should be one of the columns in the workspace table.",
    )
    order: Optional[str] = Field(
        "asc",
        description="Sorting order which can be asc for ascending or desc for descending.",
    )
    page: int = Field(0, description="Page number for pagination.")
    limit: int = Field(10000, description="Number of results per page.")
