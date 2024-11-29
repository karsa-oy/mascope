from fastapi import APIRouter, Depends, Path
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.new.auth.dependencies import admin_user
from mascope_server.api.new.users.schemas import (
    GetUsersQueryParams,
)
from mascope_server.api.new.users.service import (
    get_user,
    get_users,
)

users_router = APIRouter(prefix="/api/users", tags=["Users"])


@users_router.get("")
@api_route()
async def get_users_route(
    query_params: GetUsersQueryParams = Depends(),
    current_user=Depends(admin_user),
):
    """
    Retrieve a paginated list of all users.

    :param query_params: Query parameters for pagination and sorting.
    :type query_params: GetUsersQueryParams
    :param current_user: The current authenticated user with admin permissions or higher.
    :type current_user: User
    :return: A dictionary containing the user list and metadata.
    :rtype: dict
    """
    return await get_users(**query_params.model_dump())


@users_router.get("/{user_id}")
@api_route()
async def get_user_route(
    user_id: int = Path(..., description="ID of the user to retrieve"),
    current_user=Depends(admin_user),
):
    """
    Retrieve the user's details.

    :param user_id: The unique ID of the user to retrieve.
    :type user_id: int
    :param current_user: The current authenticated user with admin permissions or higher.
    :type current_user: User
    :return: A dictionary containing the user's details.
    :rtype: dict
    """
    return await get_user(user_id=user_id)
