"""
FastAPI dependency injection module for user management.

This module provides dependency functions specifically designed for FastAPI's
dependency injection system. These dependencies are used in route declarations
to provide user management capabilities through FastAPI Users library.
"""

from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from mascope_backend.api.new.users.user_manager.service import UserManager
from mascope_backend.db import User, get_async_session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    """
    Dependency function to provide a `SQLAlchemyUserDatabase` instance for FastAPI Users.

    This function is used to inject a database adapter for user management within the FastAPI Users library.
    It works by utilizing the injected SQLAlchemy session (retrieved via `get_async_session`) and the `User` model,
    returning a `SQLAlchemyUserDatabase` object. This adapter is then used by FastAPI Users to handle operations
    such as user creation, querying, and updating.

    :param session: An active SQLAlchemy async session, injected via dependency, defaults to Depends(get_async_session)
    :type session: AsyncSession, optional
    :yield: A SQLAlchemyUserDatabase instance for interacting with the User model.
    :rtype: AsyncGenerator[SQLAlchemyUserDatabase, None]
    """
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(user_db=Depends(get_user_db)):
    """
    Dependency to retrieve the UserManager.
    Injects the user database session.

    :param user_db: SQLAlchemyUserDatabase instance for handling user database operations,
                    defaults to Depends(get_user_db).
    :yield: An instance of `UserManager` for managing user operations.
    :rtype: UserManager
    """
    yield UserManager(user_db)
