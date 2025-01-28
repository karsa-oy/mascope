import inspect
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
from mascope_server.socket.notifications import (
    UserNotification,
    emit_sio_event,
    handle_reloads,
    handle_notifications,
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
    token_access: bool = False,
    public: bool = False,
):
    """
    A decorator for FastAPI route handlers that provides:
    1. Authentication enforcement by default (unless marked as public)
    2. Standardized response formatting
    3. Consistent error handling
    4. Optional token-based access for external service/agents/packages

    By default, all routes require authentication via auth user dependency injection.
    Routes must either:
    - Include auth user dependency (e.g., user=Depends(guest_user))
    - Or be explicitly marked as public with @api_route(public=True)

    Usage:
    Protected route (requires authentication):

        @router.get("/some-protected-path")
        @api_route()
        async def name_of_protected_route(user=Depends(guest_user)):
            ...

    Public route (no authentication):

        @router.get("/some-public-path")
        @api_route(public=True)
        async def name_of_public_route():
            ...

    Custom auth level with specific status code"
        @router.post("/some-admin-path")
        @api_route(status_code=201)
        async def name_of_admin_route(user=Depends(admin_user)):
            ...

    :param status_code: HTTP status code to be used for successful responses, defaults to 200.
    :type status_code: int, optional
    :param token_access: Flag to indicate if the route allows access via an access token (for Jupyter or external access).
                           If set to True, the endpoint is accessible via a Bearer token in addition to standard JWT authentication.
    :type token_access: bool, optional
    :param public: Flag to explicitly mark route as public (no auth)
    :type public: bool, optional
    :return: The wrapped route handler function with standardized response formatting and exception handling.
    :rtype: Callable
    """

    def decorator(func: Callable):
        # Step 1: Configure route access token settings
        func.token_access = token_access

        # Step 2: Verify route security - either must be public or have auth dependency
        if not public:
            signature = inspect.signature(func)
            if "user" not in signature.parameters:
                runtime.logger.error("Please check the route definition")
                error_message = (
                    f"Configuration error in route '{func.__name__}'\n"
                    f"All routes must either:\n"
                    f"1. Include auth user dependency (e.g., user=Depends(guest_user))\n"
                    f"2. Be explicitly marked as public with @api_route(public=True)\n"
                    f"Please update the route definition accordingly."
                )
                raise ValueError(error_message)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Step 3: Log authenticated user information if available
                user = kwargs.get("user")
                if user:
                    runtime.logger.trace(f"User:\n{pretty_repr(user.to_dict())}")

                # Step 4: Execute the route handler
                result = await func(*args, **kwargs)

                # Step 5: Prepare response headers
                headers = {}
                if result is not None and "process_id" in result:
                    headers["Process-ID"] = result.pop("process_id")

                # Step 6: Return formatted JSON response
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
