from sqlalchemy import select

from mascope_backend.api.new.users.exceptions import UsernameAlreadyExistsException
from mascope_backend.db import User, async_session


async def check_username_exists(username: str) -> None:
    """
    Check if a username already exists in the database.

    :param username: The username to check.
    :type username: str
    :raises UsernameAlreadyExistsException: If the username already exists.
    """
    async with async_session() as session:
        query = select(User).filter(User.username == username)
        result = await session.execute(query)
        existing_user = result.scalar_one_or_none()

    if existing_user:
        raise UsernameAlreadyExistsException(username=username)
