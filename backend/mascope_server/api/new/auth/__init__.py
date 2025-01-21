from fastapi_users import FastAPIUsers
from mascope_server.db.models import User
from mascope_server.api.new.users.user_manager.dependencies import get_user_manager
from mascope_server.api.new.auth.backend import (
    auth_backend_jwt,
    auth_backend_access_token,
    get_enabled_backends,
)


# FastAPI Users setup with authentication with both backends
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend_jwt, auth_backend_access_token],
)


# publicly available exports
__all__ = [
    "fastapi_users",
    "auth_backend_jwt",
    "auth_backend_access_token",
    "get_enabled_backends",
]
