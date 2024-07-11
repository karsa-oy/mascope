from copy import deepcopy
from functools import wraps
from typing import Callable, Any, Dict, List, Tuple
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from mascope_lib.util import beautify_func_name
from mascope_server.api_sio import sio
from mascope_server.db.id import gen_id
from ..exceptions import (
    process_exception,
    ApiException,
    handle_exception,
    api_e_response_json,
)
from ..models.pydantic_models.user_notification_pydantic_model import UserNotification


# TODO_notification delete after refactoring
async def emit_sio_event(
    event_name: str,
    notification: dict = None,
    room: str = None,
    sid: str = None,
):
    """
    Utility function to emit a Socket.IO event to a specified room.

    :param event_name: The name of the Socket.IO event to emit.
    :param notification: The notification to send with the event.
    :param room: The room to which the event should be emitted.
    :param sid: Optional. The session ID of the client. Used to send direct messages if needed.
    """
    # Emit without notification if event_name ends with '_reload'
    if event_name.endswith("_reload"):
        await sio.emit(event_name, room=room, namespace="/")
    else:
        # Emit the event to the specified room
        await sio.emit(event_name, notification, room=room, namespace="/")

        # Check if the user has moved from the room; if so, send them a direct message
        if sid and room != sid and room not in sio.rooms(sid, namespace="/"):
            await sio.emit(event_name, notification, room=sid, namespace="/")


async def send_progress_user_notification(
    notification: UserNotification, increment: float = None
):
    # Create a deep copy of the notification to ensure the original is not modified
    notification_copy = deepcopy(notification)

    # Extract internal metadata and clean up the data dictionary
    room_ids = notification_copy.data.pop("_room_ids", [])
    instrument_room = notification_copy.data.pop("_instrument_room", None)
    sid = notification_copy.data.pop("_sid", None)

    total_samples = notification_copy.data.pop("_total_samples", None)
    item_index = notification_copy.data.pop("_item_index", None)

    # total_batches = notification_copy.data.pop("_total_batches", None)
    batch_weight = notification_copy.data.pop("_batch_weight", None)
    batch_index = notification_copy.data.pop("_batch_index", None)

    # Clear any keys that start with an underscore as they are meant for internal use only
    keys_to_remove = [
        key for key in notification_copy.data.keys() if key.startswith("_")
    ]
    for key in keys_to_remove:
        notification_copy.data.pop(key, None)

    # If no other data remains, set data to None
    if not notification_copy.data:
        notification_copy.data = None

    # Calculate progress based on the notification type and provided increment
    if (
        notification_copy.type
        in [
            "match_compute_sample",
            "calibration_mz_fit",
            "calibration_mz_apply",
            "calibration_mz_calibrate_sample",
            "import_sample_items",
            "process_sample_item",
        ]
        and increment
    ):
        notification_copy.progress = int(increment * 100)
    if notification_copy.type == "match_compute_batch":
        if total_samples is not None and item_index is not None:
            notification_copy.progress = int(
                ((item_index + increment) / total_samples) * 100
            )
            notification_copy.message = f"Computing sample batch matches, processing sample {item_index + 1}/{total_samples}"
    if notification_copy.type == "rematch_batches":
        notification_copy.progress = int(
            (batch_index - 1 + increment) * batch_weight * 100
        )
    if notification_copy.type == "sample_batch_export_peaks":
        if total_samples is not None and item_index is not None:
            notification_copy.progress = int(
                ((item_index + increment) / total_samples) * 100
            )
            notification_copy.message = f"Exporting peak data, processing sample {item_index + 1}/{total_samples}"

    # Emit the notification to all specified rooms
    for room_id in room_ids:
        await emit_user_notification(notification_copy, room_id, sid)
    # for istrument room don't check if the user has moved from the room -> no sid is provided
    if instrument_room:
        await emit_user_notification(notification_copy, instrument_room)


async def emit_user_notification(
    notification: UserNotification = None,
    room_id: str = None,
    sid: str = None,
):
    """
    Utility function to emit a Socket.IO event to a specified room_id.

    :param notification: The notification to send with the event.
    :param room_id: The room to which the event should be emitted.
    :param sid: Optional. The session ID of the client. Used to send direct messages if needed.
    """
    notification_dict = notification.dict(exclude_none=True)
    if room_id:
        await sio.emit(
            "user_notification", notification_dict, room=room_id, namespace="/"
        )

    # Check if the user has moved from the room; if so, send them a direct message
    if sid and room_id != sid and room_id not in sio.rooms(sid, namespace="/"):
        await sio.emit("user_notification", notification_dict, room=sid, namespace="/")


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
    include_data: bool = True,
    include_message: bool = False,
    success_message: str = None,
    error_message: str = None,
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
    :param include_data: Flag to include the result of the route handler as encoded json object in the response, defaults to True.
    :type include_data: bool, optional
    :param include_message: Flag to include a success message in the response, defaults to False.
    :type include_message: bool, optional
    :param success_message: Custom success message to include in the response if include_message is True.
                            Defaults to a generic "Operation successful" message if not provided.
    :type success_message: str, optional
    :param error_message: Custom error message to include in the response if include_message is True.
    :type error_message: str, optional
    :return: The wrapped route handler function with standardized response formatting and exception handling.
    :rtype: Callable
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                headers = {}
                if result is not None and "process_id" in result:
                    headers["Process-ID"] = result.pop(
                        "process_id"
                    )  # Move process_id to headers

                content: Dict[str, Any] = {}
                if include_data:
                    content.update(jsonable_encoder(result))
                if include_message:
                    message = result.get("message") if result else None
                    content["message"] = (
                        message or success_message or "Operation successful"
                    )
                    message_logs = result.get("message_logs") if result else None
                    if message_logs is not None:
                        content["message_logs"] = message_logs
                return JSONResponse(
                    status_code=status_code,
                    content=content,
                    headers=headers,
                )

                # TODO_notifications move message forming to controllers, example delete_sample_item
                # return JSONResponse(
                #     status_code=status_code,
                #     content=jsonable_encoder(result),
                #     headers=headers,
                # )
            except ApiException as e:
                return api_e_response_json(e)
            except Exception as e:
                context_message = (
                    error_message or f"Failed to {beautify_func_name(func.__name__, 3)}"
                )
                return handle_exception(e, context_message)

        return wrapper

    return decorator


async def handle_reloads(reload_events, kwargs, result):
    """Emit reload events based on the given configurations."""
    for event_name, room in reload_events:
        room_id = kwargs.get(room)
        if not room_id and result:
            room_id = result.get(room) or result.get("data").get(room)
        if room_id is not None:
            await sio.emit(event_name, room=room_id, namespace="/")


async def handle_notifications(rooms, notification, kwargs, result, sid):
    """Emit notifications to specified rooms."""
    for room in rooms:
        room_id = kwargs.get(room)
        if not room_id and result:
            # TODO_data wrapper
            room_id = result.get(room) or result.get("data").get(room)
        # for istrument room don't check if the user has moved from the room -> no sid is provided
        if room_id and room == "instrument":
            await emit_user_notification(notification, room_id)
        if room_id is not None and room != "instrument":
            await emit_user_notification(notification, room_id, sid)


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
                        await handle_reloads(error_reload, kwargs, None)

                    if not independent_transaction and parent_id:
                        # Re-raise warning exceptions to be caught in parent handler
                        user_message = f"Warning during {beautify_func_name(func.__name__)}. {e.user_message}"
                        raise ApiException(user_message, e.tech_message, e.status_code)
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
