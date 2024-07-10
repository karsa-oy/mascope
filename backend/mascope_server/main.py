# Import this here to avoid "free(): invalid pointer" error on Linux
from mascope_hardware.tofwerk.lib.TwTool import *

import socketio
import uvicorn

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from mascope_server.api_sio import sio
from mascope_server.api.exceptions import handle_exception
from mascope_server.api.routes import routers

from mascope_server.config import config

from mascope_server.db import init_db

from .logger import setup_rich_logger

fastapi_app = FastAPI()

setup_rich_logger()

@fastapi_app.on_event("startup")
async def startup_event():
    """Run at application startup"""
    await init_db()


# CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Process-ID"],  # Expose custom process-id header
)


@fastapi_app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Custom exception handler for Pydantic validation errors. This handler is invoked when request data validation fails
    due to schema constraints defined in Pydantic models.

    :param request: The request object.
    :type request: Request
    :param exc: The RequestValidationError exception instance containing details about the validation errors.
    :type exc: RequestValidationError
    :return: A structured HTTP response indicating the validation errors.
    :rtype: JSONResponse
    """
    context_message = "Validation error"
    return handle_exception(exc, context_message, response_type="http")


@fastapi_app.exception_handler(ValueError)
async def value_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
    """
    Custom exception handler for ValueError exceptions. This handler is invoked when an operation or function receives
    an argument that has the right type but an inappropriate value.

    :param request: The request object.
    :type request: Request
    :param exc: The ValueError exception instance containing details about what caused the error.
    :type exc: ValueError
    :return: A structured HTTP response indicating the value errors.
    :rtype: JSONResponse
    """
    context_message = "Invalid value"
    return handle_exception(exc, context_message, response_type="http")


@fastapi_app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for the FastAPI app. This handler is invoked for any unhandled exceptions
    that occur during the processing of a request, serving as a catch-all for exceptions that are not
    explicitly caught by more specific route exception handlers.

    :param request: The request object. It may be used for extracting additional information about the request,
                    such as the endpoint being accessed, the request method, and any query parameters or headers.
    :param exc: The exception that was raised. This is the unhandled exception that has propagated up to the global handler.
    :return: An appropriate HTTP response based on the exception, ensuring that the application responds gracefully to unexpected errors.
    :rtype: JSONResponse
    """
    context_message = "An error occurred"
    # Handle the exception and get the response
    return handle_exception(exc, context_message, response_type="http")


# Include all routers
for router in routers:
    fastapi_app.include_router(router)

# Initialize ASGI app with socket.io and FastAPI app
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)


def run():
    """Entry point to run Mascope server"""
    uvicorn.run(
        "mascope_server.main:app",
        host="0.0.0.0" if config.env.mode == "development" else "127.0.0.1",
        port=config.server.port,
        reload=(config.env.mode == "development"),
        log_level='warning'
    )


if __name__ == "__main__":
    run()
