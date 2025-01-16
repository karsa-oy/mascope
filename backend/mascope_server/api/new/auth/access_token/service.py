import json
from sqlalchemy import select, update
from mascope_server.db import async_session
from mascope_server.db.models import AccessToken, User
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.new.auth import auth_backend_access_token


async def get_access_token(user: User, strategy, service_name: str) -> str:
    """
    Gets an access token for the specified user and service. If no token exists,
    generates a new one.

    :param user: The authenticated user
    :type user: User
    :param strategy: The authentication strategy for issueing the access token
    :type strategy: AuthenticationBackend
    :param service_name: Name of the service (e.g., "file-converter")
    :type service_name: str
    :return: The access token string
    :rtype: str
    """
    async with async_session() as session:
        # Query existing token for the user and service
        token_query = await session.execute(
            select(AccessToken)
            .where(AccessToken.user_id == user.id)
            .where(AccessToken.service_name == service_name)
        )
        token = token_query.scalar_one_or_none()

        if token:
            return token.token

        # Generate new token if none exists
        response = await generate_access_token(user, strategy, service_name)

        # Extract token from response
        data = json.loads(response.body.decode())
        return data["access_token"]


async def generate_access_token(user, strategy, service_name: str):
    """
    Generates an access token for the current authenticated user.

    This function uses the access token authentication backend to log the user in
    and return an access token, which is stored in the database.
    """
    response = await auth_backend_access_token.login(strategy, user)
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

    return response


@api_controller()
async def remove_access_tokens(user, strategy, service_name: str):
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
        for token in tokens:
            await auth_backend_access_token.logout(strategy, user, token.token)

    return {
        "message": f"All {service_name} access tokens for user {user.username} have been removed."
    }
