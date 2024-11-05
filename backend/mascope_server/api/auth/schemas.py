from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field
from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    """Schema to read user data, typically used in responses to provide user details."""

    id: int = Field(..., description="Unique identifier of the user (Primary Key).")
    email: EmailStr = Field(
        ...,
        description=(
            "User's email address. This is used as the unique login credential in the authentication flow. "
            "Although the specs of OAuth2 login form refers to this as `username`, it actually expects the user's email "
            "address here for authentication."
        ),
    )
    is_active: bool = Field(
        ..., description="Indicates if the user account is active and can log in."
    )
    is_superuser: bool = Field(
        ..., description="Designates whether the user has superuser privileges."
    )
    is_verified: bool = Field(
        ..., description="Indicates whether the user's email is verified."
    )
    username: str = Field(
        ...,
        description="Name of the user, used for display purposes (not for login).",
    )
    role_id: int = Field(
        ...,
        description="Role identifier of the user, linked to user role permissions.",
    )
    registered_at: datetime = Field(
        ..., description="Timestamp indicating when the user registered."
    )

    model_config = {
        "from_attributes": True  # Allows Pydantic to work with SQLAlchemy models
    }


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a new user. Provides fields required for user registration."""

    email: EmailStr = Field(
        ...,
        description="User's email address. This will be used as the login credential.",
    )
    password: str = Field(
        ...,
        description="User's password for authentication. Will be hashed upon creation.",
    )
    is_active: Optional[bool] = Field(
        default=True,
        description="Sets whether the user account is active upon creation.",
    )
    is_superuser: Optional[bool] = Field(
        default=False,
        description="Specifies if the user will have superuser privileges upon creation.",
    )
    is_verified: Optional[bool] = Field(
        default=False, description="Specifies whether the user's email is verified."
    )
    username: str = Field(
        ...,
        description="Username for display purposes. Note: This is not used for login.",
    )
    role_id: int = Field(
        default=1,
        description="Role ID assigned to the user (e.g., '1' for regular users).",
    )

    model_config = {"from_attributes": True}


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating existing user information. Fields can be partially updated."""

    email: Optional[EmailStr] = Field(
        None,
        description="Updated email address. If not provided, the current email remains unchanged.",
    )
    password: Optional[str] = Field(
        None,
        description="New password for the user. If not provided, the password remains unchanged.",
    )
    is_active: Optional[bool] = Field(
        None,
        description="Set to True or False to activate or deactivate the user account.",
    )
    is_superuser: Optional[bool] = Field(
        None, description="Set to True to grant or revoke superuser privileges."
    )
    is_verified: Optional[bool] = Field(
        None, description="Set to True or False to mark the user as verified or not."
    )
    username: Optional[str] = Field(
        None,
        description="Updated username for display purposes. Note: This is not used for login.",
    )
    role_id: Optional[int] = Field(
        None, description="Updated role ID to assign a new role to the user."
    )

    model_config = {"from_attributes": True}
