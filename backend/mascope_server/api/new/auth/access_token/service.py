import json
from sqlalchemy import select, update
from mascope_server.db import async_session
from mascope_server.db.models import AccessToken, User
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.new.auth.backend import auth_backend_access_token
from mascope_server.api.new.auth.strategies.database import (
    get_database_strategy_context,
)
from mascope_server.api.new.auth.exceptions import InvalidTokenException
from mascope_server.api.new.auth.access_token.validation import (
    validate_service_access_token,
)

from mascope_server.runtime import runtime


@api_controller()
async def get_access_token(user: User, service_name: str) -> str:
    """
    Gets an access token for the specified user and service.
    Raises InvalidTokenException if token is missing or invalid.

    :param user: The authenticated user
    :type user: User
    :param service_name: Name of the service (e.g., "file-converter")
    :type service_name: str
    :return: The access token string if valid
    :rtype: str
    :raises: InvalidTokenException if token invalid/missing
    """
    async with async_session() as session:
        # Query existing token for the user and service
        token_query = await session.execute(
            select(AccessToken)
            .where(AccessToken.user_id == user.id)
            .where(AccessToken.service_name == service_name)
        )
        token = token_query.scalar_one_or_none()

        if not token:
            raise InvalidTokenException(
                "You don't have access to this service. Please log in to Mascope again to refresh your access."
            )

        try:
            await validate_service_access_token(token.token, service_name)
            return token.token
        except InvalidTokenException as e:
            raise InvalidTokenException(
                "Your access to this service has expired. Please log in to Mascope again to refresh your access."
            ) from e


@api_controller()
async def generate_access_token(user, service_name: str):
    """
    Generates an access token for the current authenticated user.

    This function uses the access token authentication backend to log the user in
    and return an access token, which is stored in the database.
    """
    async with get_database_strategy_context() as database_strategy:
        response = await auth_backend_access_token.login(database_strategy, user)
    # Decode the response body and extract the token
    data = json.loads(response.body.decode())
    token = data["access_token"]
    # Update token type
    async with async_session() as session:
        await session.execute(
            update(AccessToken)
            .where(AccessToken.token == token)
            .values(service_name=service_name)
        )
        await session.commit()

    runtime.logger.debug(
        f"{user.username} access token for {service_name} is generated"
    )
    return response


@api_controller()
async def remove_access_tokens(user, service_name: str):
    """
    Removes access tokens for the specified service associated with the current authenticated user.

    This function retrieves access tokens linked to the user and then logs out
    each token using the access token authentication backend.
    """
    async with async_session() as session:
        # Query all access tokens associated with the user
        tokens_query = await session.execute(
            select(AccessToken)
            .where(AccessToken.user_id == user.id)
            .where(AccessToken.service_name == service_name)
        )
        tokens = tokens_query.scalars().all()

        if not tokens:
            return {"message": f"No access tokens found for user `{user.username}`."}

        # Use the backend logout to destroy each token
        async with get_database_strategy_context() as database_strategy:
            for token in tokens:
                await auth_backend_access_token.logout(
                    database_strategy, user, token.token
                )

    return {
        "message": f"All {service_name} access tokens for user {user.username} have been removed."
    }


@api_controller()
async def regenerate_access_token(user, service_name: str):
    """Remove existing tokens and generate new one."""
    await remove_access_tokens(user=user, service_name=service_name)
    return await generate_access_token(user=user, service_name=service_name)
