"""
Acquisition workspace management routes.

This module provides endpoints for automatic creation and cleanup
of acquisition workspaces based on available instruments.
"""

from fastapi import APIRouter, Depends, Query
from mascope_backend.api.new.auth.dependencies import guest_user, owner_user
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.workspace.acquisition.service import (
    get_acquisition_workspace,
    create_acquisition_workspaces,
    delete_acquisition_workspaces,
)
from mascope_backend.api.models.workspace.acquisition.schemas import (
    GetAcquisitionWorkspaceQueryParams,
)

acquisition_workspaces_router = APIRouter(
    prefix="/acquisition", tags=["Acquisition Workspace Management"]
)


@acquisition_workspaces_router.get("")
@api_route(token_access=True)
async def get_acquisition_workspace_route(
    query_params: GetAcquisitionWorkspaceQueryParams = Query(),
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
    return await get_acquisition_workspace(**query_params.model_dump())


@acquisition_workspaces_router.post("")
@api_route(status_code=201)
async def create_acquisition_workspaces_route(user=Depends(owner_user)):
    """Auto-create missing acquisition workspaces for all instruments.

    Creates acquisition workspaces for instruments that don't have them yet.
    This endpoint is primarily used for:
    - System initialization and setup
    - Testing and development
    - Manual workspace creation when automatic creation fails

    :param user: The current authenticated user with owner permissions.
    :type user: User
    :return: A dictionary containing the summary of created workspaces.
    :rtype: dict
    :raises ForbiddenAccessException: If user doesn't have owner permissions.
    """
    return await create_acquisition_workspaces()


@acquisition_workspaces_router.delete("")
@api_route()
async def delete_acquisition_workspaces_route(user=Depends(owner_user)):
    """Auto-delete orphaned acquisition workspaces for instruments that no longer exist.

    Removes acquisition workspaces for instruments that have no sample files.
    This endpoint is useful for:
    - System cleanup and maintenance
    - Testing and development
    - Data consistency checks

    Safety Notes:
    - Only deletes workspaces for instruments with zero sample files
    - Does not affect workspaces with valid existing instruments
    - Cannot accidentally delete workspaces with data

    :param user: The current authenticated user with owner permissions.
    :type user: User
    :return: A dictionary containing the summary of deleted workspaces.
    :rtype: dict
    :raises ForbiddenAccessException: If user doesn't have owner permissions.
    """
    return await delete_acquisition_workspaces()
