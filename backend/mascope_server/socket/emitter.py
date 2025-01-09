"""
Central event emitter for internal application events.

This module provides a central event system for handling internal application state 
changes that may result in socket.io communications. It separates internal event 
handling from Socket.IO client-server communication.

Client-Server:
Frontend -> socket.emit('subscribe') -> @sio.event handler -> Do something
Internal:
API/Service -> event_emitter.emit() -> @event_emitter.on handler -> socket.emit -> Frontend
"""

from typing import Dict, List, Callable
from asyncio import Queue
from mascope_server.runtime import runtime


class EventEmitter:
    """
    Event emitter for handling internal application events.
    """

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._queue = Queue()

    def on(self, event: str):
        """
        Decorator for registering event handlers.

        NOTE: When running with uvicorn in development mode (reload=True), event registration
        happens in both parent and child processes.

        :param event: The name of the event to register the handler for.
        :type event: str
        :return: A decorator to register the handler function.
        :rtype: Callable
        """

        def decorator(handler: Callable):
            if event not in self._handlers:
                self._handlers[event] = []
            self._handlers[event].append(handler)
            return handler

        return decorator

    async def emit(self, event: str, *args, **kwargs):
        """
        Trigger an event and call all registered handlers for it.

        :param event: The name of the event to trigger.
        :type event: str
        :param args: Positional arguments to pass to the event handlers.
        :type args: tuple
        :param kwargs: Keyword arguments to pass to the event handlers.
        :type kwarge event: str
        """
        if event in self._handlers:
            for handler in self._handlers[event]:
                try:
                    await handler(*args, **kwargs)
                except Exception as e:
                    runtime.logger.error(
                        f"Error in event handler for {event}: {str(e)}"
                    )


# Global event emitter instance
event_emitter = EventEmitter()
