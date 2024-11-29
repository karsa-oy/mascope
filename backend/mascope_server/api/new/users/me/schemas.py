from typing import Optional
from pydantic import Field, field_validator, model_validator
from fastapi_users import schemas


class UserUpdateMe(schemas.BaseUserUpdate):
    """
    Schema for updating the current authenticated user.
    Only `username` and `password` fields are accepted for update.

    Any other fields included in the update request will raise a validation error.
    """

    username: Optional[str] = Field(
        None,
        description="Updated username for display purposes. Note: This is not used for login.",
    )
    password: Optional[str] = Field(
        None,
        description="New password for the user. If not provided, the password remains unchanged.",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, username):
        """
        Validates that `username` is not an empty string.

        :param username: The username provided for update.
        :raises ValueError: If the username is an empty string.
        :return: The username if it is valid.
        """
        if username is not None and username.strip() == "":
            raise ValueError("The username cannot be an empty string.")
        return username

    @model_validator(mode="before")
    @classmethod
    def validate_allowed_fields(cls, values):
        """
        This validator checks that only `username` and `password` fields are accepted for update.
        Any other fields provided in the payload will raise a validation error.

        :param values: Dictionary of fields being updated.
        :type values: dict
        :raises ValueError: If any field other than `username` or `password` is included.
        :return: Filtered dictionary containing only allowed fields.
        :rtype: dict
        """
        allowed_fields = {"username", "password"}
        invalid_fields = {key for key in values if key not in allowed_fields}

        if invalid_fields:
            raise ValueError(
                f"You can not self-update these fields: {', '.join(invalid_fields)}."
            )
        # Only keep allowed fields
        return {key: value for key, value in values.items() if key in allowed_fields}
