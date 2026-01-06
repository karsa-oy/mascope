"""Access token validation."""

from mascope_backend.api.new.auth.access_token.util import get_token_service
from mascope_backend.api.new.auth.exceptions import InvalidTokenException
from mascope_backend.api.new.auth.strategies.database import (
    get_database_strategy_context,
)
from mascope_backend.runtime import runtime


async def validate_service_access_token(access_token: str, service_name: str):
    """
    Validate service access token and return associated user.

    :param access_token: Access token string for service
    :type access_token: str
    :param service_name: Expected service name
    :type service_name: str
    :return: User instance if token is valid
    :raises InvalidTokenException: If token is invalid or service mismatch
    """
    try:
        # Step 1. Basic token validation
        if not isinstance(access_token, str):
            raise InvalidTokenException("Invalid token format: not a string")

        # Step 2. Token validation using access token strategy
        from mascope_backend.api.new.users.user_manager.util import (
            get_user_manager_context,
        )

        async with get_database_strategy_context() as database_strategy:
            async with get_user_manager_context() as user_manager:
                user = await database_strategy.read_token(access_token, user_manager)
                if not user:
                    raise InvalidTokenException(
                        "Token validation failed, no associated user found"
                    )

                # Verify service name
                token_service = await get_token_service(access_token)
                if token_service != service_name:
                    raise InvalidTokenException(
                        f"The provided token is not authorized for {service_name}. Please try to refresh the token."
                    )

                return user

    except InvalidTokenException as e:
        runtime.logger.error(f"User's service token validation failed: {str(e)}")
        raise
    except Exception as e:
        runtime.logger.error(f"Service token validation failed: {str(e)}")
        raise InvalidTokenException("Token validation failed") from e
