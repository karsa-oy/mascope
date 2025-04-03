from typing import Optional
from pydantic import Field, field_validator, model_validator
from fastapi_users import schemas
from mascope_backend.api.new.users.exceptions import InvalidFieldsException
from mascope_backend.api.new.users.me.exceptions import (
    PasswordMismatchException,
    SamePasswordException,
)


class UserUpdateMe(schemas.BaseUserUpdate):
    """
    Schema for updating non-sensitive user fields of the current authenticated user.
    Only `username` field is accepted for update.

    Any other fields included in the update request will raise a validation error.
    """

    username: Optional[str] = Field(
        None,
        description="Updated username for display purposes. Note: This is not used for login.",
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
        This validator checks that only non-sensitive fields `username` are accepted for update.
        Any other fields provided in the payload will raise a validation error.

        :param values: Dictionary of fields being updated.
        :type values: dict
        :raises ValueError: If any field other than `username` or `password` is included.
        :return: Filtered dictionary containing only allowed fields.
        :rtype: dict
        """
        allowed_fields = {"username"}
        invalid_fields = {key for key in values if key not in allowed_fields}

        if invalid_fields:
            raise InvalidFieldsException(
                f"You can not self-update these fields: {', '.join(invalid_fields)}"
            )

        return values


class UserUpdateMeCredentials(schemas.BaseUserUpdate):
    """
    Schema for updating sensitive user credentials of the current authenticated user.

    Only `current_password` and `new_password` fields are accepted for update.
    Any other fields included in the update request will raise a validation error.
    """

    current_password: str = Field(
        ..., description="Current password required for verification"
    )
    new_password: str = Field(..., description="New password to set")
    verify_new_password: str = Field(..., description="Verify the new password")

    @model_validator(mode="before")
    @classmethod
    def validate_allowed_fields(cls, values):
        """Validate only allowed credential fields are present."""
        allowed_fields = {"current_password", "new_password", "verify_new_password"}
        invalid_fields = {key for key in values if key not in allowed_fields}

        # Check provided fields
        if invalid_fields:
            raise InvalidFieldsException(
                f"Invalid fields for credentials update: {', '.join(invalid_fields)}"
            )

        return values

    @model_validator(mode="after")
    def verify_passwords(self):
        """Verify provided passwords."""
        if self.current_password == self.new_password:
            raise SamePasswordException()
        if self.new_password != self.verify_new_password:
            raise PasswordMismatchException()
        return self
