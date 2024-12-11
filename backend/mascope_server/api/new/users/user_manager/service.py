"""
User management service module for Mascope user management.

This module contains the `UserManager` class extending FastAPI Users' class `BaseUserManager`.
It implements core lifecycle hooks and logic for user management in the Mascope server,
including registration, password updates, token management, and custom behaviors
such as access token cleanup for external services like Jupyter.
"""

from typing import Any, Dict, Optional
from fastapi import Request
from fastapi_users import BaseUserManager, IntegerIDMixin
from fastapi_users import models
from mascope_server.app.socket import sio
from mascope_server.db.models import User
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_server.api.new.auth.config import auth_settings
from mascope_server.api.new.users import exceptions
from mascope_server.api.new.users.schemas import UserCreate
from mascope_server.api.new.users.access_token.service import delete_user_access_tokens

from mascope_server.runtime import runtime


async def emit_user_events(user: Optional[User] = None):
    """
    Emit socket events for user changes, optionally also to
    targeted to a specific user.

    :param user: The FastAPI users' user model
    """
    await sio.emit("user_reload_all", namespace="/")
    if user:
        await sio.emit("user_reload_me", room=f"user-{user.id}", namespace="/")
    return


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """
    Responsible for managing user-related operations, including registration,
    password reset, email verification, and token management, etc.

    This class extends the FastAPI Users `BaseUserManager` and adds custom logic for handling
    user management in the Mascope server. See BaseUserManager for more examples.

    :param IntegerIDMixin: Mixin for managing users with integer-based IDs.
    :param BaseUserManager: FastAPI Users' base user manager with core user handling logic.
    :raises exceptions.UserAlreadyExists: Raised when trying to create a user that already exists.
    :return: Instance of a newly created or managed user.
    :rtype: models.UP
    """

    reset_password_token_secret = auth_settings.RESET_PASSWORD_TOKEN_SECRET
    reset_password_token_lifetime_seconds = (
        auth_settings.RESET_PASSWORD_TOKEN_LIFETIME_SECONDS
    )
    reset_password_token_audience = auth_settings.RESET_PASSWORD_TOKEN_AUDIENCE
    verification_token_secret = auth_settings.VERIFICATION_TOKEN_SECRET
    verification_token_lifetime_seconds = (
        auth_settings.VERIFICATION_TOKEN_LIFETIME_SECONDS
    )
    verification_token_audience = auth_settings.VERIFICATION_TOKEN_AUDIENCE

    async def get(self, id: models.ID) -> models.UP:
        """
        Get a user by id.

        :param id: Id. of the user to retrieve.
        :raises UserNotExists: The user does not exist.
        :return: A user.
        """
        user = await self.user_db.get(id)

        if user is None:
            raise NotFoundException(f"User with ID '{id}' not found")

        return user

    async def create(
        self,
        user_create: UserCreate,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> models.UP:
        """
        Create a user in database.

        Triggers the on_after_register handler on success.

        :param user_create: The UserCreate model to create.
        :param safe: If True, sensitive values like is_superuser or is_verified
        will be ignored during the creation, defaults to False.
        :param request: Optional FastAPI request that
        triggered the operation, defaults to None.
        :raises UserAlreadyExists: A user already exists with the same e-mail.
        :return: A new user.
        """
        await self.validate_password(user_create.password, user_create)

        existing_user = await self.user_db.get_by_email(user_create.email)
        if existing_user is not None:
            raise exceptions.UserEmailAlreadyExistsException(user_create.email)

        user_dict = (
            user_create.create_update_dict()
            if safe
            else user_create.create_update_dict_superuser()
        )
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)

        created_user = await self.user_db.create(user_dict)

        await self.on_after_register(created_user, request)

        return created_user

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        runtime.logger.info(f"User {user.username} was registered.")
        await emit_user_events(user)

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        runtime.logger.info(
            f"User {user.username} has forgot the password. Reset token: {token}"
        )

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        runtime.logger.info(
            f"Verification requested for user {user.username}. Verification token: {token}"
        )

    async def on_after_update(
        self,
        user: models.UP,
        update_dict: Dict[str, Any],
        request: Optional[Request] = None,
    ) -> None:
        """
        Perform logic after successful user update.

        :param user: The updated user
        :param update_dict: Dictionary with the updated user fields.
        :param request: Optional FastAPI request that
        triggered the operation, defaults to None.
        """
        runtime.logger.info(f"User `{user.username}` updated.")
        # Logout user if their password is updated? Revoke tokens logic?
        if "password" in update_dict:
            runtime.logger.info(f"User `{user.username}` password was changed.")
            await delete_user_access_tokens(user_id=user.id)
        await emit_user_events(user)
        return  # pragma: no cover

    async def on_after_delete(
        self,
        user: User,
        request: Optional[Request] = None,
    ):
        """
        Perform logic after successful user delete.

        :param user: The deleted user
        """
        await emit_user_events(user)
