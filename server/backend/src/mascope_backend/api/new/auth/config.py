"""
Core authentication configuration including JWT, cookies, and access tokens settings.
"""

from pydantic import BaseModel

from mascope_backend.api.new.auth.access_token.config import AccessTokenConfig
from mascope_backend.api.new.auth.secrets import jwt_secret_key
from mascope_backend.runtime import runtime


# TODO_configuration for auth
class AuthConfig(BaseModel):
    """
    Configuration settings related to user authentication and secrets.
    Should be securely stored in the environment variables
    """

    # Main JWT Token settings for user authentication
    JWT_SECRET_KEY: str = (
        jwt_secret_key  # PRIVATE_KEY used for signing and verifying JWT tokens
    )
    # Token lifetime - 360 days in seconds (JWT expiration)
    JWT_EXPIRATION_SECONDS: int = 360 * 24 * 60 * 60
    JWT_AUDIENCE: list = ["mascope-users:auth"]  # Audience claim for token validation
    JWT_ALGORITHM: str = (
        "HS256"  # Algorithm used for signing the JWT (HMAC with SHA-256)
    )

    # Cookie settings for web-based JWT storage
    COOKIE_NAME: str = "mascope_auth"  # Name of the authentication cookie
    # Lifetime of the cookie - 360 days in seconds (matches JWT expiration)
    COOKIE_MAX_AGE_SECONDS: int = 360 * 24 * 60 * 60
    COOKIE_SECURE: bool = (
        runtime.mode == "prod"
    )  # to send cookies only over HTTPS, True if in production, False if in dev
    COOKIE_HTTP_ONLY: bool = (
        True  # Set cookies as HTTPOnly to prevent access from JavaScript
    )

    # Password reset token settings
    RESET_PASSWORD_TOKEN_SECRET: str = (
        "SECRET_RESET"  # Separate secret for password reset tokens
    )
    RESET_PASSWORD_TOKEN_LIFETIME_SECONDS: int = (
        3600  # Expiration time for reset tokens
    )
    RESET_PASSWORD_TOKEN_AUDIENCE: str = (
        "mascope-users:reset"  # Audience for password reset tokens
    )

    # Email verification token settings
    VERIFICATION_TOKEN_SECRET: str = (
        "SECRET_VERIFY"  # Separate secret for email verification tokens
    )
    VERIFICATION_TOKEN_LIFETIME_SECONDS: int = (
        3600  # Expiration time for email verification tokens
    )
    VERIFICATION_TOKEN_AUDIENCE: str = (
        "mascope-users:verify"  # Audience for email verification tokens
    )

    # Role access levels for RBAC
    # Role names correspond to the role_id values in the database (access_level)
    ROLE_ACCESS_LEVELS: dict = {"guest": 100, "editor": 200, "admin": 300, "owner": 400}

    # Access token settings
    access_token: AccessTokenConfig = AccessTokenConfig()


auth_settings = AuthConfig()
