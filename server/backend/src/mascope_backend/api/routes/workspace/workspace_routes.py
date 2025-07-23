from fastapi import APIRouter, Depends
from fastapi import APIRouter, Depends, Query
from mascope_backend.api.new.auth.dependencies import (
    editor_user,
    guest_user,
)
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.workspace.workspace_controller import (
    get_workspaces,
    get_workspace,
    create_workspace,
    update_workspace,
    delete_workspace,
)
from mascope_backend.api.models.workspace.workspace_pydantic_model import (
    WorkspaceCreate,
    WorkspaceUpdate,
    GetWorkspacesQueryParams,
)
from mascope_backend.api.routes.workspace.acquisition.routes import (
    acquisition_workspaces_router,
)

workspace_router = APIRouter(prefix="/api/workspaces", tags=["Workspace"])
workspace_router.include_router(acquisition_workspaces_router)


@workspace_router.get("")
@api_route(token_access=True)
async def get_workspaces_route(
    query_params: GetWorkspacesQueryParams = Query(),
    user=Depends(guest_user),
):
    """Retrieve a list of workspaces.

    :param query_params: Query parameters for sorting and pagination, defaults to Depends().
    :type query_params: GetWorkspacesQueryParams, optional
    :param user: The current authenticated user, defaults to Depends(guest_user).
    :type user: User, optional
    :return: A dictionary containing total count and list of workspaces.
    :rtype: dict
    """
    return await get_workspaces(**query_params.model_dump())


@workspace_router.get("/{workspace_id}")
@api_route()
async def get_workspace_route(workspace_id: str, user=Depends(guest_user)):
    """Retrieve details of a specific workspace by ID.

    :param workspace_id: The unique identifier of the workspace.
    :type workspace_id: str
    :param user: The current authenticated user, defaults to Depends(guest_user).
    :type user: User, optional
    :return: A dictionary containing the workspace details.
    :rtype: dict
    """
    return await get_workspace(workspace_id)


@workspace_router.patch("/{workspace_id}")
@api_route()
async def update_workspace_route(
    workspace_id: str, workspace: WorkspaceUpdate, user=Depends(editor_user)
):
    """Update an existing workspace's details.

    :param workspace_id: The unique identifier of the workspace.
    :type workspace_id: str
    :param workspace: The workspace update data.
    :type workspace: WorkspaceUpdate
    :param user: The current authenticated user with editor permissions, defaults to Depends(editor_user).
    :type user: User, optional
    :return: A dictionary containing the updated workspace details.
    :rtype: dict
    """
    return await update_workspace(workspace_id, workspace)


@workspace_router.post("")
@api_route(status_code=201)
async def create_workspace_route(workspace: WorkspaceCreate, user=Depends(editor_user)):
    """Create a new workspace.

    :param workspace: The workspace creation data.
    :type workspace: WorkspaceCreate
    :param user: The current authenticated user with editor permissions, defaults to Depends(editor_user).
    :type user: User, optional
    :return: A dictionary containing the newly created workspace's details.
    :rtype: dict
    """
    return await create_workspace(workspace)


@workspace_router.delete("/{workspace_id}")
@api_route()
async def delete_workspace_route(workspace_id: str, user=Depends(editor_user)):
    """Delete a specific workspace by ID.

    :param workspace_id: The unique identifier of the workspace.
    :type workspace_id: str
    :param user: The current authenticated user with editor permissions, defaults to Depends(editor_user).
    :type user: User, optional
    :return: A dictionary confirming deletion (if applicable).
    :rtype: dict or None
    """
    return await delete_workspace(workspace_id)
