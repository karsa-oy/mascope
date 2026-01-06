from fastapi import APIRouter

from mascope_backend.api.new.auth import (
    auth_backend_jwt,
    fastapi_users,
)
from mascope_backend.api.new.auth.access_token.routes import access_token_router


# main Auth router
auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])

# Include JWT-based authentication and registration routes
auth_router.include_router(fastapi_users.get_auth_router(auth_backend_jwt))

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
