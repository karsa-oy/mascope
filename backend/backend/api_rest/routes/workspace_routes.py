from fastapi import APIRouter

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
)

workspace_router = APIRouter()


@workspace_router.get("/api/workspaces")
async def get_workspaces_route(
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_workspaces(sort, order, page, limit)


@workspace_router.get("/api/workspaces/{workspace_id}")
async def get_workspace_by_id_route(workspace_id: str):
    return await get_workspace(workspace_id)


@workspace_router.post("/api/workspaces")
async def create_workspace_route(workspace: WorkspaceCreate):
    return await create_workspace(workspace)


@workspace_router.patch("/api/workspaces/{workspace_id}")
async def update_workspace_route(workspace_id: str, workspace: WorkspaceUpdate):
    return await update_workspace(workspace_id, workspace)


@workspace_router.delete("/api/workspaces/{workspace_id}")
async def delete_workspace_route(workspace_id: str):
    return await delete_workspace(workspace_id)
