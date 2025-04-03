from fastapi import APIRouter, Body, Depends, Request
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.new.users.first_owner.schemas import FirstOwnerCreate
from mascope_backend.api.new.users.first_owner.util import (
    check_first_owner_registration,
)
from mascope_backend.api.new.users.user_manager.dependencies import get_user_manager
from mascope_backend.api.new.users.exceptions import InvalidUsernameException
from mascope_backend.api.new.users.service import register_user
from mascope_backend.api.new.users.user_manager.service import UserManager

first_owner_router = APIRouter(prefix="/api/users/first-owner", tags=["First Owner"])


@first_owner_router.get("/status")
@api_route(public=True)
async def check_first_owner_sign_up_status_route():
    """
    Check if owner signup is available by verifying no users exist in the system.

    The endpoint follows fail-fast pattern:
    - Returns 200 only when owner signup is possible (no users exist)
    - Returns 403 when signup is not available (users exist)

    :return: Status message indicating if owner signup is possible
    :rtype: dict
    :raises FirstOwnerRegistrationNotAvailableException: If any users exist in system (403)
    """
    # Step 1: Check if owner signup is available by verifying no users exist
    await check_first_owner_registration()

    # Step 2: If check passes (no exception raised), return success response
    return {
        "message": "Please sign-up Mascope first owner account",
    }


@first_owner_router.post("")
@api_route(status_code=201, public=True)
async def register_first_owner_route(
    request: Request,
    first_owner_create: FirstOwnerCreate = Body(...),
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    Register the first owner user if no users exist in the system.
    This endpoint is unprotected but requires a valid server secret.

    :param request: The current HTTP request
    :param first_owner_create: The first owner registration details with server secret
    :param user_manager: User manager instance
    :return: The registered owner details
    """
    # Step 1: Check if this is the first user
    await check_first_owner_registration()

    # Step 2: Check for explicit null values in the raw request body
    body = await request.json()
    if "username" in body and body["username"] is None:
        raise InvalidUsernameException()

    # Step 3: Create owner user (privileges are set in schema validation)
    return await register_user(
        user_create=first_owner_create, user_manager=user_manager, safe=False
    )
