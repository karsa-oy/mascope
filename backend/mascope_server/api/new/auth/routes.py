from fastapi import APIRouter, Depends
from mascope_server.api.new.auth.auth_backend import (
    fastapi_users,
    auth_backend_cookie,
    auth_backend_access_token,
)
from mascope_server.api.new.auth.dependencies import current_active_user
from mascope_server.api.new.auth.service import (
    generate_access_token,
    remove_access_tokens,
)
from mascope_server.api.new.users.schemas import UserRead, UserCreate


# main Auth router
auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])

# Include JWT-based authentication and registration routes
auth_router.include_router(fastapi_users.get_auth_router(auth_backend_cookie))
auth_router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))


# Access token-based routes for Jupyter server or external API access
access_token_router = APIRouter(prefix="/access_token")


@access_token_router.post("/generate", name="auth:access-token.generate")
async def access_token_generate_route(
    user=Depends(current_active_user),
    strategy=Depends(auth_backend_access_token.get_strategy),
):
    """
    API route to generate a new access token.

    This endpoint generates an access token for the authenticated user,
    which can be used to authenticate requests to external services as Jupyter server.
    """
    return await generate_access_token(user, strategy)


@access_token_router.post("/remove", name="auth:access-token.remove")
async def access_token_remove_route(
    user=Depends(current_active_user),
    strategy=Depends(auth_backend_access_token.get_strategy),
):
    """
    API route to remove all of a user's access tokens.

    This endpoint deletes all access tokens associated with the authenticated user.
    """
    return await remove_access_tokens(user, strategy)


# Include the access token router within the main auth router for nested routing
auth_router.include_router(access_token_router)


# add more routes such as password reset and email verification etc, check library code
# auth_router.include_router(
#     fastapi_users.get_reset_password_router(),
# )
#
# auth_router.include_router(
#     fastapi_users.get_verify_router(UserRead),
# )
