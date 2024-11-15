from functools import wraps
from typing import Callable, List, Tuple
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from rich.pretty import pretty_repr

from mascope_lib.util import beautify_func_name
from mascope_server.db.id import gen_id
from mascope_server.api.lib.exceptions.api_exceptions import (
    process_exception,
    ApiException,
    handle_exception,
    api_e_response_json,
)
from mascope_server.api.lib.notifications.api_notification import (
    emit_sio_event,
    handle_reloads,
    handle_notifications,
)
from mascope_server.api.lib.notifications.api_notification_pydantic_model import (
    UserNotification,
)

from mascope_server.runtime import runtime


def api_controller(emit_reload_events: List[Tuple[str, str]] = [], error_message=None):
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
            independent_transaction = kwargs.get("independent_transaction", False)
            try:
                result = await func(*args, **kwargs)
                if independent_transaction:
                    # Emit reload events
                    for event_name, room_key in emit_reload_events:
                        room_id = (
                            kwargs.get(room_key)
                            or result.get(room_key)
                            or result.get("data").get(room_key)
                            if room_key
                            else None
                        )
                        if room_id:
                            await emit_sio_event(event_name=event_name, room=room_id)
                return result
            except ApiException as e:
                # Handle already processed exceptions
                context_message = (
                    error_message or f"Failed to {beautify_func_name(func.__name__)}"
                )
                user_message = f"{context_message}. {e.user_message}"
                raise ApiException(user_message, e.tech_message, e.status_code)
            except Exception as e:
                # Use a custom error message if provided, otherwise default to the function name
                context_message = (
                    error_message or f"Failed to {beautify_func_name(func.__name__)}"
                )
                raise process_exception(e, context_message)

        return wrapper

    return decorator


def api_route(
    status_code: int = 200,
    jupyter_access: bool = False,
):
    """
    A decorator for route handler functions to standardize the response structure and handle exceptions.

    This decorator wraps route handler functions to automatically format their successful responses into
    a consistent JSON structure, including optional success messages. It also catches ApiException instances
    to return standardized error responses.

    The decorator allows for customization of the HTTP status code for successful responses, inclusion of
    a data payload, and addition of custom success messages.

    Usage:
    @api_route(status_code=201, include_message=True, success_message="Entity created successfully")
    async def your_route_handler(...):
        # Your handler implementation

    :param status_code: HTTP status code to be used for successful responses, defaults to 200.
    :type status_code: int, optional
    :param jupyter_access: Flag to indicate if the route allows access via an access token (for Jupyter or external access).
                           If set to True, the endpoint is accessible via a Bearer token in addition to standard JWT authentication.
    :type jupyter_access: bool, optional
    :return: The wrapped route handler function with standardized response formatting and exception handling.
    :rtype: Callable
    """

    def decorator(func: Callable):
        # Attach access attributes to function
        func.jupyter_access = jupyter_access

        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Log user information if available
                user = kwargs.get("user")
                if user:
                    runtime.logger.trace(f"User:\n{pretty_repr(user.to_dict())}")

                # Execute the function
                result = await func(*args, **kwargs)
                headers = {}
                # Move process_id to headers
                if result is not None and "process_id" in result:
                    headers["Process-ID"] = result.pop("process_id")

                return JSONResponse(
                    status_code=status_code,
                    content=jsonable_encoder(result),
                    headers=headers,
                )
            except ApiException as e:
                return api_e_response_json(e)
            except Exception as e:
                context_message = f"Error in {beautify_func_name(func.__name__)}"
                return handle_exception(e, context_message)

        return wrapper

    return decorator


def api_controller_background_task(
    success_notification_rooms: List[str] = [],
    success_reload: List[Tuple[str, str]] = [],
    error_notification_rooms: List[str] = [],
    error_reload: List[Tuple[str, str]] = [],
):
    """
    A decorator for background task controller functions to standardize response structure, handle exceptions, and emit Socket.IO events.

    This decorator wraps a controller function, executes it, and depending on the outcome (success or failure), updates the payload, and emits Socket.IO events.

    The decorator handles two main scenarios:
    1. When the wrapped function completes successfully, it updates the payload with success details and emits the specified success events.
    2. When the wrapped function raises an ApiException or any other exception, it updates the payload with error details and emits the specified error events.

    Returns:
        - A decorator that wraps asynchronous controller functions for background tasks with standardized success and error handling.
    Usage:
        @api_controller_background_task(
            success_emit_events=[("event_name_success", "room_key_success")],
            error_emit_events=[("event_name_failure", "room_key_failure")],
            default_payload={"initial": "data"},  TODO the pydantic model can be used
            success_message="Task completed successfully",
            error_message="Task failed"
        )
        async def my_background_task_function(*args, **kwargs):
            # Function body


    :param success_emit_events: A list of tuples, where each tuple contains an event name and a room key for successful operations. The room key is used to target the event emission. Defaults to an empty list.
    :type success_emit_events: List[Tuple[str, str]], optional
    :param error_emit_events: List of tuples for error event names and room keys. Similar to success_emit_events but used for error scenarios. Defaults to an empty list.
    :type error_emit_events: List[Tuple[str, str]], optional
    :param default_payload: Default payload for event emissions. A dictionary containing default data to include in the event emission payload. Defaults to None.
    :type default_payload: dict, optional
    :param success_message: A custom message to include in the payload when the operation succeeds. Defaults to None, which will use a generic success message based on the function name.
    :type success_message: str, optional
    :param error_message: A custom message to include in the payload when the operation fails. Defaults to None, which will use a generic error message based on the function name.
    :type error_message: str, optional
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            sid = kwargs.get("sid")
            independent_transaction = kwargs.get("independent_transaction", False)
            process_id = kwargs.get("process_id", gen_id(8))  # Generate if not provided
            parent_id = kwargs.get("parent_id", None)

            notification = UserNotification(
                process_id=process_id,
                parent_id=parent_id,
                progress=100,
                type=func.__name__,
                status="pending",
                message=f"{func.__name__.replace('_', ' ').title()} is processing.",
            )
            try:
                result = await func(*args, **kwargs)
                # Update notification on success
                notification.status = "success"
                notification.message = result.get("message") if result else None
                notification.data = (
                    result.get("_notification_data", None) if result else None
                )

                # Handle success user notifications
                await handle_notifications(
                    success_notification_rooms, notification, kwargs, result, sid
                )
                # Handle success reload notifications
                # Emit reload events for remat_batch even if called as a part of remath_batches
                if independent_transaction or (
                    func.__name__ == "rematch_batch" and parent_id
                ):
                    await handle_reloads(success_reload, kwargs, result)

                return result
            except ApiException as e:
                if e.status_code == 200:
                    # Handle warning notifications, status code 200
                    notification.status = "warning"
                    # notification.message = f"Warning during {beautify_func_name(func.__name__)}. {e.user_message}"
                    notification.message = e.user_message
                    notification.error = {"detail": e.tech_message}
                    #  Emit warning user notifications for both independent and dependent transactions
                    await handle_notifications(
                        error_notification_rooms, notification, kwargs, None, sid
                    )
                    if independent_transaction or (
                        func.__name__ == "rematch_batch" and parent_id
                    ):
                        await handle_reloads(error_reload, kwargs, e.tech_message)

                    if not independent_transaction and parent_id:
                        # Re-raise warning exceptions to be caught in parent handler
                        raise ApiException(
                            e.user_message, e.tech_message, e.status_code
                        )
                else:
                    # Update the payload with ApiException error details
                    notification.status = "error"
                    notification.message = f"Failed to {beautify_func_name(func.__name__)}.  {e.user_message}"
                    notification.error = {"detail": e.tech_message}
                    #  Emit error user notifications only if this is an independent transaction
                    if independent_transaction:
                        # NOTE: for the error_notification_rooms the sio room id should be provided
                        # in the controller kwargs, since the result is not available
                        await handle_notifications(
                            error_notification_rooms, notification, kwargs, None, sid
                        )
                        await handle_reloads(error_reload, kwargs, None)
                    # If not an independent transaction, re-raise the ApiException
                    else:
                        # Handle already processed exceptions
                        context_message = (
                            f"Failed to {beautify_func_name(func.__name__)}"
                        )
                        user_message = f"{context_message}. {e.user_message}"
                        raise ApiException(user_message, e.tech_message, e.status_code)

            except Exception as e:
                context_message = f"Failed to {beautify_func_name(func.__name__)}"
                api_exc = process_exception(e, context_message)

                #  Emit error user notifications only if this is an independent transaction
                if independent_transaction:
                    # Update the payload with error details
                    notification.status = "error"
                    notification.message = api_exc.user_message
                    notification.error = {"detail": api_exc.tech_message}
                    # NOTE: for the error_notification_rooms the sio room id should be provided
                    # in the controller kwargs, since the result is not available
                    await handle_notifications(
                        error_notification_rooms, notification, kwargs, None, sid
                    )
                    await handle_reloads(error_reload, kwargs, None)
                # If not an independent transaction, re-raise the ApiException
                else:
                    raise api_exc from e

        return wrapper

    return decorator
