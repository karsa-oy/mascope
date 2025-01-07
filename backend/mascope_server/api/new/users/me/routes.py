from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from mascope_server.db.models import User
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.new.auth.dependencies import guest_user, current_active_user
from mascope_server.api.new.users.exceptions import InvalidUsernameException
from mascope_server.api.new.users.user_manager.dependencies import get_user_manager
from mascope_server.api.new.users.service import update_user, get_user
from mascope_server.api.new.users.user_manager.service import UserManager
from mascope_server.api.new.users.schemas import UserUpdate
from mascope_server.api.new.users.me.exceptions import InvalidCurrentPasswordException
from mascope_server.api.new.users.me.schemas import (
    UserUpdateMe,
    UserUpdateMeCredentials,
)

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


@me_router.patch("/creds")
@api_route()
async def update_credentials_route(
    credentials_update: UserUpdateMeCredentials,
    user: User = Depends(guest_user),
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    Update user credentials (password) for the current authenticated user.

    Steps:
    1. Validates provided credentials update data (handled by schema)
    2. Verifies current password matches user's password
    3. Updates to the new password if all validations pass

    :param credentials_update: Contains current password, new password and verification
    :type credentials_update: UserUpdateMeCredentials
    :param user: The current authenticated user
    :type user: User
    :param user_manager: User manager instance for authentication and updates
    :type user_manager: UserManager
    :return: Updated user details
    :rtype: dict
    :raises CurrentPasswordIncorrectException: If current password is invalid
    """
    # Step 1: Verify current password
    credentials = OAuth2PasswordRequestForm(
        username=user.email,
        password=credentials_update.current_password,
    )
    authenticated_user = await user_manager.authenticate(credentials)
    if not authenticated_user:
        raise InvalidCurrentPasswordException()

    # Step 2: Update to new password
    return await update_user(
        user_id=user.id,
        user_update=UserUpdate(password=credentials_update.new_password),
        user_manager=user_manager,
    )
