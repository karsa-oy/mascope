from fastapi import APIRouter, Depends

from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.new.auth.dependencies import admin_user, owner_user
from mascope_backend.api.new.roles.schemas import GetRolesQueryParams
from mascope_backend.api.new.roles.service import get_roles


roles_router = APIRouter(prefix="/api/roles", tags=["Roles"])


@roles_router.get("/admin")
@api_route()
async def get_roles_route(
    query_params: GetRolesQueryParams = Depends(),
    user=Depends(admin_user),
):
    """
    Retrieve roles up to 'editor' for admins.

    :param query_params: Filtering options for roles.
    :type query_params: GetRolesQueryParams
    :param user: The currently authenticated admin user.
    :type user: User
    :return: A dictionary containing filtered roles.
    :rtype: dict
    """
    query_params.role_name_max = "editor"  # Restrict roles to 'editor' and below
    return await get_roles(**query_params.model_dump())


@roles_router.get("/owner")
@api_route()
async def owner_get_roles_route(
    query_params: GetRolesQueryParams = Depends(),
    user=Depends(owner_user),
):
    """
    Retrieve roles up to 'admin' for owners.

    :param query_params: Filtering options for roles.
    :type query_params: GetRolesQueryParams
    :param user: The currently authenticated owner user.
    :type user: User
    :return: A dictionary containing filtered roles.
    :rtype: dict
    """
    return await get_roles(**query_params.model_dump())
