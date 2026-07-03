from fastapi import APIRouter, Depends

from mascope_backend.api.lib.rate_limit import rate_limit
from mascope_backend.api.new.auth import (
    auth_backend_jwt,
    fastapi_users,
)
from mascope_backend.api.new.auth.access_token.routes import access_token_router


# main Auth router
auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])

# Include JWT-based authentication and registration routes.
# Rate-limit by client IP to blunt password brute-forcing / credential stuffing
# against the login endpoint (also covers logout in this sub-router, harmlessly).
auth_router.include_router(
    fastapi_users.get_auth_router(auth_backend_jwt),
    dependencies=[Depends(rate_limit(times=10, seconds=60, scope="auth-login"))],
)

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
