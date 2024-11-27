"""
User password management service.

This module handles admin/owner password management for other users.
"""

import secrets
import string
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.new.users.schemas import UserUpdate
from mascope_server.api.new.users.service import update_user
from mascope_server.api.new.users.service_user_manager import UserManager


def generate_random_password(length: int = 12) -> str:
    """
    Generates a secure random password.

    :param length: Length of the password.
    :return: A random password string.
    """
    characters = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(characters) for _ in range(length))


@api_controller()
async def reset_user_password(user_id: int, user_manager: UserManager) -> dict:
    """
    Resets a user's password to a new random value.

    :param user_id: ID of the user whose password will be reset.
    :param user_manager: Instance of the UserManager.
    :return: The new password.
    """
    # Step 1: Generate a random password
    new_password = generate_random_password()

    # Step 2: Create the update model
    user_update = UserUpdate(password=new_password)

    # Step 3: Update the user's password
    user = (
        await update_user(
            user_id=user_id, user_update=user_update, user_manager=user_manager
        )
    ).get("data")

    # Step 4: Return the new password
    return {
        "message": f"Password for user {user.username} has been reset.",
        "data": {"new_password": new_password},
    }
