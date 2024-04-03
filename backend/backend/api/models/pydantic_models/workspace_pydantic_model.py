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


class WorkspaceInDB(WorkspaceBase):
    workspace_id: str = Field(..., description="ID of the workspace")
    workspace_utc_created: Optional[str] = Field(
        None, description="Creation timestamp of the workspace"
    )
    workspace_utc_modified: Optional[str] = Field(
        None, description="Last modification timestamp of the workspace"
    )

    class Config:
        orm_mode = True
