# TODO_error_handling
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError


class ApiException(Exception):
    def __init__(self, user_message, tech_message, status_code):
        super().__init__()
        self.user_message = user_message
        self.tech_message = tech_message
        self.status_code = status_code


class NotFoundException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def process_exception(e: Exception, context_message: str) -> ApiException:
    print(e)
    error_message = str(e)
    if isinstance(e, SQLAlchemyError):
        user_message = f"{context_message}: database operation failed."
        tech_message = error_message
        status_code = 400  # Bad Request
    elif isinstance(e, ApiException):
        print(e)
        user_message = e.user_message
        tech_message = e.tech_message
        status_code = e.status_code
    elif isinstance(e, HTTPException):
        user_message = f"{context_message}: {e.detail}."
        tech_message = error_message
        status_code = e.status_code
    elif isinstance(e, ValueError):
        user_message = f"{context_message}: invalid value."
        tech_message = error_message
        status_code = 400  # Bad Request
    else:
        user_message = f"{context_message}: unexpected error."
        tech_message = error_message
        status_code = 500  # Internal Server Error

    return ApiException(user_message, tech_message, status_code)
