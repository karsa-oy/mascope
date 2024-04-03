from functools import wraps
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Callable, Any, Dict
from ..exceptions import (
    process_exception,
    ApiException,
    handle_exception,
    api_e_response_json,
)


def api_controller(error_message=None):
    """
    A decorator for controller functions to handle exceptions and standardize error responses.

    This decorator wraps a controller function, catches any exceptions thrown during its executions. If an ApiException is caught
    (meaning that some other controller was called and it has already raised the processed ApiException), it is re-raised to be
    handled by FastAPI's exception handlers. For non-processed exceptions, an ApiException is raised with a custom or default error
    message, providing additional context about where the error occurred.

    Usage:
        @api_controller(error_message="Custom error message")
        async def some_controller_function(...):
            ...

    :param error_message: Custom error message to use if an exception occurs, defaults to None. If None, a default message based on the function name is used.
    :type error_message: str, optional
    :return: The decorated controller function wrapped in a try-except block for exception handling.
    :rtype: Callable
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ApiException as e:
                # Handle already processed exceptions
                raise e
            except Exception as e:
                # Use a custom error message if provided, otherwise default to the function name
                context_message = error_message or f"Failed during {func.__name__}"
                raise process_exception(e, context_message)

        return wrapper

    return decorator


def api_route(
    status_code_success: int = 200,
    include_data: bool = True,
    include_message: bool = False,
    success_message: str = None,
):
    """
    A decorator for route handler functions to standardize the response structure and handle exceptions.

    This decorator wraps route handler functions to automatically format their successful responses into
    a consistent JSON structure, including optional success messages. It also catches ApiException instances
    to return standardized error responses.

    The decorator allows for customization of the HTTP status code for successful responses, inclusion of
    a data payload, and addition of custom success messages.

    Usage:
    @api_route(status_code_success=201, include_message=True, success_message="Entity created successfully")
    async def your_route_handler(...):
        # Your handler implementation

    :param status_code_success: HTTP status code to be used for successful responses, defaults to 200.
    :type status_code_success: int, optional
    :param include_data: Flag to include the result of the route handler as encoded json object in the response, defaults to True.
    :type include_data: bool, optional
    :param include_message: Flag to include a success message in the response, defaults to False.
    :type include_message: bool, optional
    :param success_message: Custom success message to include in the response if include_message is True.
                            Defaults to a generic "Operation successful" message if not provided.
    :type success_message: str, optional
    :return: The wrapped route handler function with standardized response formatting and exception handling.
    :rtype: Callable
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                content: Dict[str, Any] = {}
                if include_data:
                    content = jsonable_encoder(result)
                if include_message:
                    content["message"] = success_message or "Operation successful."
                return JSONResponse(status_code=status_code_success, content=content)
            except ApiException as e:
                return api_e_response_json(e)

        return wrapper

    return decorator
