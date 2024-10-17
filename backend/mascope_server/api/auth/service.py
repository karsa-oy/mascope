"""
User management service module for Mascope Server authentication.

This module contains the `UserManager` class that handles user creation, password management, and
user event hooks such as registration, password reset requests, email verification, etc.
"""

from typing import Optional

from fastapi import Request
from fastapi_users import BaseUserManager, IntegerIDMixin
from fastapi_users import exceptions, models, schemas
from mascope_server.api.auth.config import auth_settings
from mascope_server.api.auth.schemas import UserCreate
from mascope_server.db.models import User

from mascope_server.runtime import runtime


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

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        runtime.logger.info(f"User {user.username} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")

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
            raise exceptions.UserAlreadyExists()

        user_dict = (
            user_create.create_update_dict()
            if safe
            else user_create.create_update_dict_superuser()
        )
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)
        user_dict["role_id"] = 1

        created_user = await self.user_db.create(user_dict)

        await self.on_after_register(created_user, request)

        return created_user
