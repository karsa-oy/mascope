from fastapi import APIRouter, Depends
from ..utils.api_features import api_route
from ..controllers.workspace_controller import (
    get_workspaces,
    get_workspace,
    create_workspace,
    update_workspace,
    delete_workspace,
)
from ..models.pydantic_models.workspace_pydantic_model import (
    WorkspaceCreate,
    WorkspaceUpdate,
    GetWorkspacesQueryParams,
)

workspace_router = APIRouter()


@workspace_router.get("/api/workspaces")
@api_route()
async def get_workspaces_route(query_params: GetWorkspacesQueryParams = Depends()):
    return await get_workspaces(**query_params.dict())


@workspace_router.get("/api/workspaces/{workspace_id}")
@api_route()
async def get_workspace_route(workspace_id: str):
    return await get_workspace(workspace_id)


@workspace_router.patch("/api/workspaces/{workspace_id}")
@api_route(include_message=True, success_message="Workspace updated successfully")
async def update_workspace_route(workspace_id: str, workspace: WorkspaceUpdate):
    return await update_workspace(workspace_id, workspace)


@workspace_router.post("/api/workspaces")
@api_route(
    status_code_success=201,
    include_message=True,
    success_message="Workspace created successfully",
)
async def create_workspace_route(workspace: WorkspaceCreate):
    return await create_workspace(workspace)


@workspace_router.delete("/api/workspaces/{workspace_id}")
@api_route(
    include_data=False,
    include_message=True,
    success_message="Workspace deleted successfully",
)
async def delete_workspace_route(workspace_id: str):
    await delete_workspace(workspace_id)
