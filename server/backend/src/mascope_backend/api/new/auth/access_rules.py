"""
API-level access rules for locked entities, extending RBAC controls from dependencies.py
"""

from typing import Type, Union

from sqlalchemy import select

from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.api.new.auth.exceptions import ForbiddenAccessException
from mascope_backend.api.new.roles.exceptions import InvalidRoleException
from mascope_backend.db import SampleBatch, SampleItem, User, Workspace, async_session


# Type alias for allowed lockable sqlalchemy models
LockableModel = Union[Type[Workspace], Type[SampleBatch], Type[SampleItem]]


async def locked_access(
    user: User,
    model: LockableModel,
    ids: Union[str, list[str]],
    min_role: str | None = None,
) -> None:
    """
    Check if user can access locked entities using SQLAlchemy models.

    :param user: Current authenticated user
    :type user: User
    :param model: SQLAlchemy model class (Workspace, SampleBatch, or SampleItem)
    :type model: LockableModel
    :param ids: Single ID or list of IDs to check
    :type ids: Union[str, list[str]]
    :param min_role: Minimum role required for locked items. None means nobody can
                     access locked items.
    :type min_role: str | None
    :raises ForbiddenAccessException: If user cannot access locked entities
    :raises InvalidRoleException: If min_role is invalid or user role is malformed
    :return: None
    :rtype: None
    """
    # Normalize ids to a list
    id_list = [ids] if isinstance(ids, str) else list(ids)
    if not id_list:
        return

    # Derive field names from model
    table_name = model.__tablename__
    id_column = model.__table__.columns[f"{table_name}_id"]
    entity_type = table_name.replace("_", " ")

    # Early exit: if min_role is None, reject if any locked entities exist
    if min_role is None:
        async with async_session() as session:
            stmt = (
                select(id_column)
                .where(id_column.in_(id_list), model.locked == 1)
                .limit(1)  # Stop at first match
            )
            if await session.scalar(stmt):
                raise ForbiddenAccessException(
                    f"Locked {entity_type}s cannot be manually modified."
                )
        return

    # Validate role configuration
    role_access_levels = auth_settings.ROLE_ACCESS_LEVELS
    required_role_id = role_access_levels.get(min_role, None)
    if required_role_id is None:
        raise InvalidRoleException(
            detail=f"The required role '{min_role}' is not defined in the configuration"
        )

    # Validate user's role configuration
    if user.role_id is None or user.role_id not in role_access_levels.values():
        raise InvalidRoleException(
            detail=(
                f"The user's role ID '{user.role_id}' "
                "is not defined in the configuration."
            )
        )

    # User has sufficient role for locked items
    if user.role_id >= required_role_id:
        return

    # Check if any items are locked - reject access if found
    async with async_session() as session:
        stmt = (
            select(id_column)
            .where(id_column.in_(id_list), model.locked == 1)
            .limit(1)  # Stop at first locked item found
        )
        if await session.scalar(stmt):
            raise ForbiddenAccessException(
                f"You do not have permission to access locked {entity_type}"
            )
