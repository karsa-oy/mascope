from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
from fastapi_users.authentication.strategy.db import (
    AccessTokenDatabase,
    DatabaseStrategy,
)
from mascope_server.api.new.auth.config import auth_settings
from mascope_server.db import get_async_session
from mascope_server.db.models import AccessToken


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
