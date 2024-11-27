"""
Access token management for other users.

It allows admins or owners to delete access tokens for other users.
"""

from sqlalchemy import delete
from mascope_server.db import async_session
from mascope_server.db.models import AccessToken, User
from mascope_server.api.lib.api_features import api_controller

from mascope_server.runtime import runtime


@api_controller()
async def delete_user_access_tokens(user_id: int) -> dict:
    """
    Deletes all access tokens associated with the specified user (by user_id).

    This function directly removes all access tokens linked to the user from the database.
    Used for admin managing of other users.

    :param user_id: The ID of the user whose tokens should be deleted.
    :return: A success message or a notification if no tokens were found.
    """
    # Step 1: Fetch the user details
    async with async_session() as session:
        user = await session.get(User, user_id)

    # Step 2: Remove all access tokens for the user
    async with async_session() as session:
        delete_query = delete(AccessToken).where(AccessToken.user_id == user_id)
        result = await session.execute(delete_query)
        await session.commit()

        if result.rowcount == 0:
            message = f"No access tokens found for user `{user.username}`."

    message = f"All access tokens for user `{user.username}` have been deleted."
    runtime.logger.info(message)
    return {"message": message}
