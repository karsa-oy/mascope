from contextlib import asynccontextmanager
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
from fastapi_users.authentication.strategy.db import (
    AccessTokenDatabase,
    DatabaseStrategy,
)
from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.db import async_session, get_async_session
from mascope_backend.db.models import AccessToken


async def get_access_token_db(session: AsyncSession = Depends(get_async_session)):
    """
    Provides a database adapter for access tokens, allowing retrieval, creation, and deletion
    of access tokens associated with users.

    This adapter is used by the authentication strategy for managing API key-based authentication.

    :param session: SQLAlchemy async session, injected via dependency.
    :return: Access token database adapter for interacting with AccessToken table.
    """
    yield SQLAlchemyAccessTokenDatabase(session, AccessToken)


# Database strategy for access token authentication (access token stored in DB)
def get_database_strategy(
    access_token_db: AccessTokenDatabase[AccessToken] = Depends(get_access_token_db),
) -> DatabaseStrategy:
    """
    Returns a DatabaseStrategy for access token authentication.

    This strategy validates access token stored in the database, associating each key with a user ID.
    Tokens expire after the defined lifetime.
    """
    return DatabaseStrategy(
        access_token_db,
        lifetime_seconds=auth_settings.access_token.ACCESS_TOKEN_EXPIRATION_SECONDS,
    )


@asynccontextmanager
async def get_access_token_db_context():
    """
    Context manager for access token database operations outside of HTTP requests.

    Used in scenarios like Socket.IO authentication where FastAPI's
    dependency injection is not available.

    :yield: Database adapter for access token operations
    :rtype: SQLAlchemyAccessTokenDatabase
    """
    async with async_session() as session:
        yield SQLAlchemyAccessTokenDatabase(session, AccessToken)


@asynccontextmanager
async def get_database_strategy_context():
    """
    Context manager for database strategy outside of HTTP requests.

    Provides access token validation capabilities in non-HTTP contexts
    like Socket.IO authentication.

    :yield: Database strategy instance
    :rtype: DatabaseStrategy
    """
    async with get_access_token_db_context() as access_token_db:
        strategy = DatabaseStrategy(
            access_token_db,
            lifetime_seconds=auth_settings.access_token.ACCESS_TOKEN_EXPIRATION_SECONDS,
        )
        yield strategy
