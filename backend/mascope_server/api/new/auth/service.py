from sqlalchemy import select
from mascope_server.db import async_session
from mascope_server.db.models import AccessToken
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.new.auth.auth_backend import auth_backend_access_token


async def generate_access_token(user, strategy):
    """
    Generates an access token for the current authenticated user.

    This function uses the access token authentication backend to log the user in
    and return an access token, which is stored in the database.
    """
    response = await auth_backend_access_token.login(strategy, user)
    return response


@api_controller()
async def remove_access_tokens(user, strategy):
    """
    Removes all access tokens associated with the current authenticated user.

    This function retrieves all access tokens linked to the user and then logs out
    each token using the access token authentication backend.
    """
    async with async_session() as session:
        # Query all access tokens associated with the user
        tokens_query = await session.execute(
            select(AccessToken).where(AccessToken.user_id == user.id)
        )
        tokens = tokens_query.scalars().all()

        if not tokens:
            return {"message": f"No access tokens found for user `{user.username}`."}

        # Use the backend logout to destroy each token
        for token in tokens:
            await auth_backend_access_token.logout(strategy, user, token.token)

    return {"message": f"All access tokens for user {user.username} have been removed."}
