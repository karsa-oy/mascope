from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users.db import SQLAlchemyUserDatabase
from mascope_server.db import async_session, get_async_session
from mascope_server.db.models import User
from mascope_server.api.new.users.service_user_manager import UserManager
from mascope_server.api.new.users import exceptions


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


async def check_username_exists(username: str) -> bool:
    """
    Check if a username already exists in the database.

    :param username: The username to check.
    :type username: str
    :return: True if the username exists, False otherwise.
    :rtype: bool
    """
    async with async_session() as session:
        query = select(User).filter(User.username == username)
        result = await session.execute(query)
        existing_user = result.scalar_one_or_none()

    if existing_user:
        raise exceptions.UsernameAlreadyExistsException(username=username)
