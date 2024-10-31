from fastapi import APIRouter, Depends
from mascope_server.api.new.auth.dependencies import current_active_user, admin_user
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.workspace.workspace_controller import (
    get_workspaces,
    get_workspace,
    create_workspace,
    update_workspace,
    delete_workspace,
)
from mascope_server.api.models.workspace.workspace_pydantic_model import (
    WorkspaceCreate,
    WorkspaceUpdate,
    GetWorkspacesQueryParams,
)

workspace_router = APIRouter()


@workspace_router.get("/api/workspaces")
@api_route()
async def get_workspaces_route(query_params: GetWorkspacesQueryParams = Depends()):
    return await get_workspaces(**query_params.model_dump())


@workspace_router.get("/api/workspaces/{workspace_id}")
@api_route()
async def get_workspace_route(workspace_id: str):
    return await get_workspace(workspace_id)


# TODO test protected route
@workspace_router.get("/api/workspaces/{workspace_id}/protected")
@api_route()
async def get_workspace_protected_route(
    workspace_id: str,
    user=Depends(current_active_user),  # Protect route by ensuring user is active
):
    # Pass the session and user to the controller function if needed
    workspace = await get_workspace(workspace_id)
    return {
        "message": f"Hello {user.username}! This is a protected workspace route",
        "workspace": workspace,
    }


# TODO test protected route for admins
@workspace_router.get("/api/workspaces/{workspace_id}/admin")
@api_route()
async def get_workspace_admin_route(
    workspace_id: str,
    user=Depends(admin_user),  # Protect route by ensuring user is active and admin
):
    # Pass the session and user to the controller function if needed
    workspace = await get_workspace(workspace_id)
    return {
        "message": f"Hello {user.username}! This is a admin protected workspace route",
        "workspace": workspace,
    }


@workspace_router.patch("/api/workspaces/{workspace_id}")
@api_route(include_message=True, success_message="Workspace updated successfully")
async def update_workspace_route(workspace_id: str, workspace: WorkspaceUpdate):
    return await update_workspace(workspace_id, workspace)


@workspace_router.post("/api/workspaces")
@api_route(
    status_code=201,
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
