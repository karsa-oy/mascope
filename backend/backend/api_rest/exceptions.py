# TODO_error_handling
import traceback
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError


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
    error_message = f"{context_message}: {str(e)}."
    traceback_info = traceback.format_exc()

    # Construct the technical message with traceback information
    tech_message = f"{error_message}\n\n{traceback_info}"
    print(tech_message)

    if isinstance(e, SQLAlchemyError):
        user_message = f"{context_message}: database operation failed."
        status_code = 400  # Bad Request
    elif isinstance(e, ApiException):
        print(e)
        user_message = e.user_message
        status_code = e.status_code
    elif isinstance(e, HTTPException):
        user_message = f"{context_message}: {e.detail}."
        status_code = e.status_code

    elif isinstance(e, ValueError):
        user_message = f"{context_message}: invalid value."
        status_code = 400  # Bad Request
    else:
        user_message = f"{context_message}: unexpected error."
        status_code = 500  # Internal Server Error

    return ApiException(user_message, tech_message, status_code)
