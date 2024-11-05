from fastapi import APIRouter
from mascope_server.api.auth.auth_backend import fastapi_users, auth_backend_cookie
from mascope_server.api.auth.schemas import UserRead, UserCreate

# Create the APIRouter and define the common prefix and tags
auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])

# Include the authentication routes using the FastAPIUsers class
auth_router.include_router(fastapi_users.get_auth_router(auth_backend_cookie))

# Include the register route for user registration
auth_router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))

# add more routes such as password reset and email verification etc, check library code
# auth_router.include_router(
#     fastapi_users.get_reset_password_router(),
# )
#
# auth_router.include_router(
#     fastapi_users.get_verify_router(UserRead),
# )
