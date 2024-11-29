from fastapi import APIRouter, Depends, Request
from mascope_server.db.models import User
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.new.auth.dependencies import guest_user, current_active_user
from mascope_server.api.new.users.exceptions import InvalidUsernameException
from mascope_server.api.new.users.util import get_user_manager
from mascope_server.api.new.users.service import update_user, get_user
from mascope_server.api.new.users.user_manager.service import UserManager
from mascope_server.api.new.users.me.schemas import UserUpdateMe

me_router = APIRouter(prefix="/api/users/me", tags=["Current User"])


@me_router.get("")
@api_route()
async def get_me_route(
    user: User = Depends(current_active_user),
):
    """
    Retrieve the current authenticated user's details.

    :param user: The current authenticated user, injected by dependency.
    :type user: User
    :return: The current user's details.
    :rtype: UserRead
    """
    return await get_user(user_id=user.id)


@me_router.patch("")
@api_route()
async def update_me_route(
    request: Request,
    user_update: UserUpdateMe,
    user: User = Depends(guest_user),
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    Update the current authenticated user's details.

    :param user_update: The updates to apply to the current user.
    :type user_update: UserUpdateMe
    :param request: The current HTTP request.
    :type request: Request
    :param user: The current authenticated user, injected by dependency.
    :type user: User
    :param user_manager: The UserManager instance.
    :type user_manager: UserManager
    :return: The updated user details.
    :rtype: UserRead
    """
    # Step 1: Check for explicit null values in the raw request body
    body = await request.json()  # Parse raw JSON body
    if "username" in body and body["username"] is None:
        raise InvalidUsernameException()

    # Step 2: Call the controller to process the update
    return await update_user(
        user_id=user.id,
        user_update=user_update,
        user_manager=user_manager,
    )
