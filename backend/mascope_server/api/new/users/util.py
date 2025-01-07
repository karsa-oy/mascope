from sqlalchemy import select
from mascope_server.db import async_session
from mascope_server.db.models import User
from mascope_server.api.new.users.exceptions import UsernameAlreadyExistsException


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
        raise UsernameAlreadyExistsException(username=username)
