import inspect
from functools import wraps
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Callable, Any, Dict, List, Tuple
from backend.server import sio
from lib.util import beautify_func_name
from ..exceptions import (
    process_exception,
    ApiException,
    handle_exception,
    api_e_response_json,
)


async def emit_sio_event(
    event_name: str, payload: dict = None, room: str = None, sid: str = None
):
    """
    Utility function to emit a Socket.IO event to a specified room.

    :param event_name: The name of the Socket.IO event to emit.
    :param payload: The data payload to send with the event.
    :param room: The room to which the event should be emitted.
    :param sid: Optional. The session ID of the client. Used to send direct messages if needed.
    """
    # Emit without payload if event_name ends with '_reload'
    if event_name.endswith("_reload"):
        await sio.emit(event_name, room=room, namespace="/")
    else:
        # Emit the event to the specified room
        await sio.emit(event_name, payload, room=room, namespace="/")

        # Check if the user has moved from the room; if so, send them a direct message
        if sid and room != sid and room not in sio.rooms(sid, namespace="/"):
            await sio.emit(event_name, payload, room=sid, namespace="/")


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
                            kwargs.get(room_key) or result.get(room_key)
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
                if include_message:
                    content["message"] = success_message or "Operation successful"
                    # Add resultmessage_logs if available
                    message_logs = result.get("message_logs") if result else None
                    if message_logs is not None:
                        content["message_logs"] = message_logs
                if include_data:
                    content.update(jsonable_encoder(result))
                return JSONResponse(status_code=status_code_success, content=content)
            except ApiException as e:
                return api_e_response_json(e)
            except Exception as e:
                context_message = f"Failed to {beautify_func_name(func.__name__, 3)}"
                return handle_exception(e, context_message)

        return wrapper

    return decorator


def api_controller_background_task(
    success_emit_events: List[Tuple[str, str]] = [],
    error_emit_events: List[Tuple[str, str]] = [],
    default_payload: dict = None,
    success_message: str = None,
    error_message: str = None,
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
            default_payload={"initial": "data"},  TODO_notifications the pydantic model can be used
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
            payload = default_payload or {}

            try:
                # Execute the wrapped function
                result = await func(*args, **kwargs)
                # Update the payload and emit success events if this is an independent transaction
                # TODO_notifications handle adding "payload data" to payload, imlement in match resource
                if independent_transaction:
                    # Update the payload with success details
                    payload.update(
                        {
                            "status": "success",
                            "progress_percentage": 100,
                            "message": success_message
                            or f"{beautify_func_name(func.__name__)} completed successfully.",
                        }
                    )

                    # Emit success events
                    for event_name, room_key in success_emit_events:
                        room_id = (
                            kwargs.get(room_key) or result.get(room_key)
                            if room_key
                            else None
                        )
                        if room_id:
                            await emit_sio_event(event_name, payload, room_id, sid)

                return result

            except ApiException as e:
                # Update the payload if this is an independent transaction
                if independent_transaction:
                    # Directly emit the error payload for already processed exceptions
                    payload.update(
                        {
                            "status": "error",
                            "progress_percentage": 100,
                            "message": f"Failed to {beautify_func_name(func.__name__)}. {e.user_message}",
                            "error": e.tech_message,
                        }
                    )
                # If not an independent transaction, re-raise the ApiException
                else:
                    # Handle already processed exceptions
                    context_message = (
                        error_message
                        or f"Failed to {beautify_func_name(func.__name__)}"
                    )
                    user_message = f"{context_message}. {e.user_message}"
                    raise ApiException(user_message, e.tech_message, e.status_code)

            except Exception as e:
                context_message = (
                    error_message or f"Failed to {beautify_func_name(func.__name__)}"
                )
                api_exc = process_exception(e, context_message)

                # Update the payload with error details if it is the independent transaction
                if independent_transaction:
                    # Update the payload with error details
                    payload.update(
                        {
                            "status": "error",
                            "progress_percentage": 100,
                            "message": api_exc.user_message,
                            "error": api_exc.tech_message,
                        }
                    )
                # If not an independent transaction, re-raise the ApiException
                else:
                    raise api_exc

            #  Emit error events only if this is an independent transaction
            if independent_transaction:
                # Emit error events
                for event_name, room_key in error_emit_events:
                    # for the error_emit_events the sio room id should be provided in the controller kwargs, since the result is not available
                    room_id = kwargs.get(room_key)
                    if room_id:
                        await emit_sio_event(event_name, payload, room_id, sid)

        return wrapper

    return decorator
