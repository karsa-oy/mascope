import uuid

import httpx
from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi_users.exceptions import InvalidPasswordException
from sqlalchemy.exc import SQLAlchemyError

from mascope_backend.api.new.roles.exceptions import InvalidRoleException
from mascope_backend.runtime import runtime


class ApiException(Exception):
    def __init__(self, user_message, tech_message, status_code):
        super().__init__()
        self.user_message = user_message
        self.tech_message = tech_message
        self.status_code = status_code


class NotFoundException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class DuplicateException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


def process_exception(e: Exception, context_message: str) -> ApiException:
    error_message = f"{context_message}. {str(e)}."
    # Opaque reference for correlating a client-visible error with the
    # server-side log entry. The traceback and internal details are only
    # logged, never returned to the client.
    error_id = uuid.uuid4().hex
    tech_message = {"error_id": error_id}

    # Use pattern matching to determine user message and status code
    match e:
        case SQLAlchemyError():
            user_message = f"{context_message}. Database operation failed."
            status_code = 400  # Bad Request

        case ApiException():
            user_message = e.user_message
            status_code = e.status_code
            # Keep payloads that application code attached on purpose
            # (e.g. raise_api_warning details consumed by the frontend).
            if isinstance(e.tech_message, dict):
                tech_message = jsonable_encoder(
                    {**e.tech_message, "error_id": error_id}
                )
            elif e.tech_message:
                tech_message = jsonable_encoder(e.tech_message)

        case InvalidPasswordException():
            # Password policy violation from UserManager.validate_password.
            user_message = str(e.reason)
            status_code = 400  # Bad Request

        case HTTPException():
            status_code = e.status_code

            match e:
                case _ if e.status_code == status.HTTP_401_UNAUTHORIZED:
                    user_message = f"{context_message}. Please sign in to the Mascope."
                case _ if (
                    e.status_code == status.HTTP_400_BAD_REQUEST
                    and str(e.detail) == "ErrorCode.LOGIN_BAD_CREDENTIALS"
                ):
                    user_message = (
                        "Invalid login credentials. Please check email and password."
                    )
                case InvalidRoleException():
                    user_message = (
                        "The role is invalid. Please contact the administrator."
                    )
                case _:
                    user_message = f"{context_message}. {e.detail}"

        # Handling for httpx timeout errors
        case httpx.TimeoutException():
            user_message = (
                f"{context_message}. Connection timed out. Please try again later."
            )
            status_code = 504  # Gateway Timeout

        case httpx.ConnectError():
            user_message = f"{context_message}. Unable to connect to the service. Please check your connection and try again."
            status_code = 503  # Service Unavailable

        case httpx.RequestError():
            user_message = (
                f"{context_message}. Error making the request to external service."
            )
            status_code = 502  # Bad Gateway

        case ValueError():
            user_message = error_message.replace("\n", "; ")
            status_code = 400  # Bad Request

        case RequestValidationError():
            error_messages = [error["msg"] for error in e.errors()]
            combined_error_message = "; ".join(error_messages)
            user_message = f"{context_message}. {combined_error_message}"
            status_code = 422  # Unprocessable entity

        case AttributeError():
            user_message = error_message
            status_code = 400  # Bad Request

        case RuntimeError():
            user_message = error_message
            status_code = 500  # Internal Server Error

        case _:  # Default case
            # Do not echo str(e) for unexpected exceptions: messages such as
            # FileNotFoundError include internal filesystem paths.
            user_message = f"{context_message}. Unexpected error."
            status_code = 500  # Internal Server Error

    # Log the exception with full traceback and context server-side
    with runtime.logger.contextualize(status_code=status_code, error_id=error_id):
        runtime.logger.exception(error_message)

    return ApiException(user_message, tech_message, status_code)


def api_e_response_json(e: ApiException):
    return JSONResponse(
        status_code=e.status_code,
        content={"error": e.user_message, "detail": e.tech_message},
    )


def handle_exception(
    e, context_message: str, response_type: str = "http"
) -> JSONResponse:
    """
    Handles exceptions by processing them and returning an appropriate response.

    :param e: The exception that was raised.
    :param context_message: A context message for better error understanding.
    :param response_type: The type of response to return, defaults to "http".
    :return: A JSONResponse for HTTP response types.
    """
    # Process the exception
    processed_exception = process_exception(e, context_message)

    # Handle based on the response type
    if response_type == "http":
        return api_e_response_json(processed_exception)
    # other response types like "sio" can be added here


def raise_api_warning(message: str, tech_message: dict, status_code: int = 200) -> None:
    """
    Raises an ApiException with a warning status code, indicating a warning during operation.

    This function creates a standardized way to raise warning level issues
    in the application. The warning will:
    1. Be logged to the server logs
    2. Be returned as a response with the specified status code
    3. Be displayed as a notification in the UI if a valid SID is available

    Status code usage:
    - 200: General warnings for both regular controllers and background tasks
    - 207: Multi-status/batch operations with partial success (some succeeded, some failed)

    Example:
    1) For general warnings (both controllers and background tasks)
        raise_api_warning(
            "Processing completed with warnings",
            {"warning_details": "..."}
        )

    2) For batch operations with partial success
        raise_api_warning(
            "Some items could not be processed",
            {"skipped_items": ["item1", "item2"]},
            status_code=207
        )

    :param message: The user-facing warning message.
    :type message: str
    :param tech_message: The technical details to include in the warning.
    :type tech_message: dict
    :param status_code: HTTP status code (200 for general warnings, 207 for multi-status operations).
    :type status_code: int
    :raises ApiException: Always raises an ApiException with the provided message and tech details.
    """
    runtime.logger.warning(message)
    raise ApiException(
        user_message=message,
        tech_message=tech_message,
        status_code=status_code,
    )
