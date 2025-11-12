"""
User management service module for Mascope user management.

This module contains the `UserManager` class extending FastAPI Users' class `BaseUserManager`.
It implements core lifecycle hooks and logic for user management in the Mascope server,
including registration, password updates, token management, and custom behaviors
such as access token cleanup for external services like Jupyter.
"""

from typing import Any, Dict, Optional
from sqlalchemy import select
from fastapi import Request, Response
from fastapi_users import BaseUserManager, IntegerIDMixin
from fastapi_users import models
from mascope_backend.db import async_session
from mascope_backend.db.models import User, Role
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.api.new.users import exceptions
from mascope_backend.api.new.users.schemas import UserCreate, UserUpdate, UserRead
from mascope_backend.api.new.auth.access_token.service import regenerate_access_token
from mascope_backend.api.new.users.access_token.service import delete_user_access_tokens
from mascope_backend.socket.records.service import (
    emit_record_created,
    emit_record_updated,
    emit_record_deleted,
)
from mascope_backend.socket.auth import (
    authenticate_socket_connection,
    SocketUnauthenticatedError,
)

from mascope_backend.runtime import runtime


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

    async def _get_user_dict_with_role(self, user: User) -> dict:
        """
        Convert User model to dict including role_name from joined Role table.

        :param user: User model instance
        :return: User dict with role_name field
        """
        async with async_session() as session:
            query = select(Role.role_name).filter(Role.role_id == user.role_id)
            result = await session.execute(query)
            role_name = result.scalar_one_or_none()
            user_data = user.to_dict()
            user_data["role_name"] = role_name

            return user_data

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

    async def update(
        self,
        user_update: UserUpdate,
        user: models.UP,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> models.UP:
        """
        Update a user in database and manage file-converter token on role change.

        :param user_update: The UserUpdate model containing
        the changes to apply to the user.
        :param user: The current user to update.
        :param safe: If True, sensitive values like is_superuser or is_verified
        will be ignored during the update, defaults to False
        :param request: Optional FastAPI request that
        triggered the operation, defaults to None.
        :return: The updated user.
        """
        old_role_id = user.role_id
        # Call parent update (this triggers on_after_update)
        updated_user = await super().update(user_update, user, safe, request)

        # Handle file-converter token on role change
        if (
            hasattr(user_update, "role_id")  # UserUpdateMe does not have role_id
            and user_update.role_id is not None
            and old_role_id != updated_user.role_id
        ):
            editor_level = auth_settings.ROLE_ACCESS_LEVELS.get("editor")
            promoted_to_editor = old_role_id < editor_level <= updated_user.role_id
            demoted_to_guest = old_role_id >= editor_level > updated_user.role_id

            if promoted_to_editor:
                await regenerate_access_token(
                    user=updated_user, service_name="file-converter"
                )
                runtime.logger.info(
                    f"Generated file-converter token for {updated_user.username}"
                )
            elif demoted_to_guest:
                await delete_user_access_tokens(
                    user_id=updated_user.id, service_name="file-converter"
                )
                runtime.logger.info(
                    f"Removed file-converter token for {updated_user.username}"
                )

        return updated_user

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        runtime.logger.info(f"User {user.username} was registered.")

        user_dict = await self._get_user_dict_with_role(user)
        validated_user_dict = UserRead.model_validate(user_dict).model_dump()
        await emit_record_created(
            record_type="user",
            record_id=str(user.id),
            record=validated_user_dict,
        )

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

    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
        response: Optional[Response] = None,
    ) -> None:
        """
        After user login:
        1. Authenticate the socket connection
        2. Generate file-converter access token for editor+ roles

        :param user: The user that is logging in
        :param request: Optional FastAPI request
        :param response: Optional response built by the transport.
        Defaults to None
        """
        try:
            # Step 1: Socket authentication
            if request and response and "set-cookie" in response.headers:
                sid = request.headers.get("x-sid")
                if not sid:
                    runtime.logger.error(
                        f"There is no sid in the request headers. User: {user.username}"
                    )
                    return

                cookie = response.headers["set-cookie"]
                jwt_token = cookie.split("mascope_auth=")[1].split(";")[0]

                # Authenticate the socket connection
                await authenticate_socket_connection(
                    sid=sid, token=jwt_token, minimum_role="guest"
                )
            # Step 2: Generate file converter access token for editor+ roles
            if user.role_id >= auth_settings.ROLE_ACCESS_LEVELS.get("editor"):
                await regenerate_access_token(user=user, service_name="file-converter")
        except SocketUnauthenticatedError as e:
            runtime.logger.error(f"Socket authentication failed after login: {str(e)}")
        except Exception as e:
            runtime.logger.error(
                f"Unexpected error during socket authentication after login: {str(e)}"
            )
        return

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

        # Revoke access tokens if password changed
        if "password" in update_dict:
            runtime.logger.info(f"User `{user.username}` password was changed.")
            await delete_user_access_tokens(user_id=user.id)

        user_dict = await self._get_user_dict_with_role(user)
        validated_user_dict = UserRead.model_validate(user_dict).model_dump()

        # Broadcast to all clients for admin views
        await emit_record_updated(
            record_type="user", record_id=str(user.id), record=validated_user_dict
        )

        # Also emit to the specific user's room for their own profile updates
        await emit_record_updated(
            record_type="user_me",
            record_id=str(user.id),
            record=validated_user_dict,
            room=f"user-{user.id}",
        )
        return

    async def on_after_delete(
        self,
        user: User,
        request: Optional[Request] = None,
    ):
        """
        Perform logic after successful user delete.

        :param user: The deleted user
        """
        await emit_record_deleted(record_type="user", record_id=str(user.id))
