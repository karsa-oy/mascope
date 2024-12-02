"""
User management CRUD service module.

This module provides core CRUD operations for user management in the Mascope server.
It extends the FastAPI Users library by combining its user management functionality
with custom operations and integrations, including role filtering, validation, etc.
"""

from typing import Optional
from sqlalchemy import asc, desc, select, func
from mascope_server.db import async_session
from mascope_server.db.models import User, Role
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_server.api.new.auth.config import auth_settings
from mascope_server.api.new.users.user_manager.service import UserManager
from mascope_server.api.new.users.schemas import UserCreate, UserRead, UserUpdate
from mascope_server.api.new.users.util import check_username_exists
from mascope_server.api.new.roles.exceptions import InvalidRoleException


@api_controller()
async def get_users(
    role_name_min: Optional[str] = None,
    role_name_max: Optional[str] = None,
    page: int = 0,
    limit: int = 10000,
    sort: str = "registered_at",
    order: str = "desc",
) -> dict:
    """
    Retrieves a paginated, sorted, and optionally filtered list of users.

    :param role_name_min: Minimum role name for filtering (inclusive), defaults to None.
    :type role_name_min: Optional[str]
    :param role_name_max: Maximum role name for filtering (inclusive), defaults to None.
    :type role_name_max: Optional[str]
    :param page: Page number for pagination, defaults to 0.
    :type page: int
    :param limit: Number of results per page, defaults to 100.
    :type limit: int
    :param sort: Column name to sort by, defaults to "registered_at".
    :type sort: str
    :param order: Sort order, either 'asc' or 'desc', defaults to "desc".
    :type order: str
    :raises NotFoundException: If no users are found in the database.
    :return: A dictionary containing the user list and metadata.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct the base query with join to Role
        query = select(User, Role.role_name).join(Role, Role.role_id == User.role_id)

        # Step 2: Apply filtering if specified
        if role_name_min or role_name_max:
            # Retrieve role levels from the configuration
            role_access_levels = auth_settings.ROLE_ACCESS_LEVELS

            if role_name_min:
                min_access_level = role_access_levels.get(role_name_min, None)
                if min_access_level is not None:
                    query = query.filter(Role.role_id >= min_access_level)

            if role_name_max:
                max_access_level = role_access_levels.get(role_name_max, None)
                if max_access_level is not None:
                    query = query.filter(Role.role_id <= max_access_level)

        # Step 2: Apply sorting
        if sort:
            query = query.order_by(
                desc(getattr(User, sort))
                if order == "desc"
                else asc(getattr(User, sort))
            )

        # Step 3: Get total count for pagination
        count_query = select(func.count()).select_from(  # pylint: disable=not-callable
            query.subquery()
        )
        total = await session.scalar(count_query)

        # Step 4: Apply pagination and execute the query
        query = query.offset(page * limit).limit(limit)
        result = await session.execute(query)

        # Step 5: Construct the response data
        users = []
        for user, role_name in result.all():
            user_data = user.to_dict()
            user_data["role_name"] = role_name
            users.append(UserRead.model_validate(user_data))

    return {
        "message": f"Retrieved {len(users)} user records.",
        "results": total,
        "data": users,
    }


@api_controller()
async def get_user(user_id: str) -> dict:
    """
    Retrieves a user by their ID.

    :param user_id: The ID of the user to retrieve.
    :type user_id: int
    :raises NotFoundException: If the user does not exist.
    :return: The user object.
    """
    async with async_session() as session:
        # Step 1: Retrieve the user by ID
        user = await session.get(User, user_id)
        if not user:
            raise NotFoundException(f"User with ID '{user_id}' not found.")

        # Step 2: Validate the user's role ID
        role_access_levels = auth_settings.ROLE_ACCESS_LEVELS
        if user.role_id is None or user.role_id not in role_access_levels.values():
            raise InvalidRoleException(
                detail=f"The user's role ID '{user.role_id}' is not defined in the configuration. Please check for configuration issues"
            )

        # Step 3: Fetch role name by joining with the Role table
        query = select(Role.role_name).filter(Role.role_id == user.role_id)
        result = await session.execute(query)
        role_name = result.scalar_one_or_none()

        if not role_name:
            raise InvalidRoleException(
                detail=f"The role ID '{user.role_id}' is not defined in the configuration. Please check for configuration issues"
            )

        # Step 4: Prepare and return the validated user data
        user_data = user.to_dict()
        user_data["role_name"] = role_name

        # Step 5: Validate and return the user read data
        validated_user = UserRead.model_validate(user_data)
        return {
            "message": f"User '{validated_user.username}' retrieved.",
            "data": validated_user,
        }


@api_controller()
async def register_user(
    user_create: UserCreate,
    user_manager: UserManager,
) -> dict:
    """
    Registers a new user in Mascope.

    :param user_create: The details of the user to be registered.
    :type user_create: UserCreate
    :param user_manager: The UserManager instance for user operations.
    :type user_manager: UserManager
    :raises UsernameAlreadyExistsException: If the username already exists.
    :raises UserAlreadyExists: If a user with the same email already exists.
    :return: The registered user's details.
    :rtype: dict
    """
    # Step 1: Check if the username already exists
    await check_username_exists(user_create.username)

    # Step 2: Create the user
    created_user = await user_manager.create(user_create, safe=True)

    # Step 3: Validate and return the registered user's details
    user = (await get_user(user_id=created_user.id))["data"]
    return {
        "message": f"User '{user.username}' registered successfully.",
        "data": user,
    }


@api_controller()
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    user_manager: UserManager,
) -> dict:
    """
    Updates a user's details.

    :param user_id: The ID of the user to update.
    :type user_id: int
    :param user_update: The updates to apply to the user.
    :type user_update: UserUpdate
    :param user_manager: The UserManager instance.
    :type user_manager: UserManager
    :param request: The current HTTP request.
    :type request: Request
    :raises NotFoundException: If the user does not exist.
    :return: The updated user details.
    """
    # Step 1: Retrieve the user
    user = await user_manager.get(user_id)

    # Step 2: Check if the new username already exists
    if user_update.username and user_update.username != user.username:
        await check_username_exists(user_update.username)

    # Step 3: Update the user
    await user_manager.update(user_update, user)

    # Step 4: Validate and return the updated user
    user = (await get_user(user_id=user_id))["data"]
    message = f"User '{user.username}' updated successfully."
    if user_update.password is not None:
        message += " Access tokens must be regenerated due to password change."
    return {
        "message": message,
        "data": user,
    }


@api_controller()
async def delete_user(user_id: int, user_manager: UserManager) -> dict:
    """
    Deletes a user by their ID.

    :param user_id: The ID of the user to delete.
    :type user_id: int
    :param user_manager: The UserManager instance.
    :type user_manager: UserManager
    :raises NotFoundException: If the user does not exist.
    :return: A success message.
    :rtype: dict
    """
    # Step 1: Fetch the user
    user = await user_manager.get(user_id)

    # Step 2: Perform the delete operation
    await user_manager.delete(user)

    return {"message": f"User '{user.username}' deleted successfully."}
