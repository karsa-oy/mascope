from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
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
