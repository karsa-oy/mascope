"""
Context managers for user management outside of FastAPI request context.

This module provides async context managers for accessing user management 
functionality in non-HTTP contexts (e.g., Socket.IO authentication, 
CLI commands). Unlike dependencies.py which is used for HTTP routes,
these utilities manage their own database sessions.
"""

from contextlib import asynccontextmanager
from fastapi_users.db import SQLAlchemyUserDatabase
from mascope_backend.db import async_session
from mascope_backend.db.models import User
from mascope_backend.api.new.users.user_manager.service import UserManager


@asynccontextmanager
async def get_user_db_context():
    """
    Context manager for user database access outside of HTTP requests.

    Used in scenarios like Socket.IO authentication
    where FastAPI's dependency injection is not available.

    :yield: Database adapter for user operations
    :rtype: SQLAlchemyUserDatabase
    """
    async with async_session() as session:
        yield SQLAlchemyUserDatabase(session, User)


@asynccontextmanager
async def get_user_manager_context():
    """
    Context manager for user management outside of HTTP requests.

    Provides user management capabilities in non-HTTP contexts like
    Socket.IO authentication or scheduled tasks.

    :yield: User manager instance
    :rtype: UserManager
    """
    async with get_user_db_context() as user_db:
        user_manager = UserManager(user_db)
        yield user_manager
