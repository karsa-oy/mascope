from fastapi_users.authentication import JWTStrategy
from mascope_backend.api.new.auth.config import auth_settings


# JWT strategy for cookie authentication
def get_jwt_strategy() -> JWTStrategy:
    """
    Returns a JWT strategy for handling user authentication via cookies.

    This function configures a JWT (JSON Web Token) strategy, which FastAPI Users uses to handle
    user authentication. The JWT is signed using a secret key and has a defined expiration time.

    :return: A configured JWT strategy for handling authentication.
    :rtype: JWTStrategy
    """
    return JWTStrategy(
        secret=auth_settings.JWT_SECRET_KEY,
        lifetime_seconds=auth_settings.JWT_EXPIRATION_SECONDS,
        token_audience=auth_settings.JWT_AUDIENCE,
        algorithm=auth_settings.JWT_ALGORITHM,
    )
