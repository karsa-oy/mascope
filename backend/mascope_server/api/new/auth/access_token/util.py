from sqlalchemy import select
from mascope_server.db import async_session
from mascope_server.db.models import AccessToken
from mascope_server.api.new.auth.exceptions import InvalidTokenException


async def get_token_service(token: str) -> str:
    """
    Get service name associated with an access token.

    :param token: The access token string
    :return: Service name if found, None otherwise
    """
    async with async_session() as session:
        result = await session.execute(
            select(AccessToken.service_name).where(AccessToken.token == token)
        )
        service_name = result.scalar_one_or_none()

        if not service_name:
            raise InvalidTokenException()

        return service_name
