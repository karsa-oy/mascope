from fastapi import APIRouter
from mascope_server.api.auth.auth_backend import fastapi_users
from mascope_server.api.users.schemas import UserRead, UserUpdate

# Create the APIRouter and define the common prefix and tags
users_router = APIRouter(prefix="/api/users", tags=["Users"])

# Include the users router to have access to /me endpoint, etc
users_router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
)
