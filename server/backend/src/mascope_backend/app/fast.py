"""
Application initialization functions.
Contains startup procedures and system checks.
"""

import uuid
import os
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from mascope_file.gc import gc_filestore
from mascope_backend.db import init_db
from mascope_backend.db.wal.engine import wal_checkpoint
from mascope_backend.api.routes import routers
from mascope_backend.api.lib.exceptions.api_exceptions import handle_exception
from mascope_backend.api.controllers.workspace.acquisition.service import (
    create_acquisition_workspaces,
)
from mascope_backend.db.ops.batch.reset_processing_status import (
    reset_stuck_processing_batches,
)

from mascope_backend.runtime import runtime


# Define the lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # --- STARTUP TASKS ---
    # Initialize database
    runtime.logger.info("Fast App startup: initializing database")
    await init_db()

    # Reset stuck processing batches
    runtime.logger.info("Fast App startup: resetting stuck processing batches")
    await reset_stuck_processing_batches()

    # Reset temp directory
    runtime.logger.info("Fast App startup: initializing temp directory")
    temp_dir = runtime.env.path("temp")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.mkdir(temp_dir)

    # Clean filestore
    runtime.logger.info("Fast App startup: garbage collecting the filestore")
    gc_filestore()

    # Initialize application components
    runtime.logger.info("Fast App startup: initializing application")
    await init_app()

    # Yield control back to FastAPI
    yield

    # --- SHUTDOWN TASKS ---
    await wal_checkpoint()


# Initialize FastAPI with the lifespan
fast = FastAPI(lifespan=lifespan)


# logging middleware
@fast.middleware("http")
async def logger_middleware(request: Request, call_next):
    worker_pid = os.getpid()

    # Make the request and receive a response
    response = await call_next(request)

    # add logging context
    with runtime.logger.contextualize(
        path=request.url.path,
        method=request.method,
        client_host=request.client.host,
        request_id=str(uuid.uuid4()),
        status_code=response.status_code,
        worker_pid=worker_pid,
    ):
        # Log request details and query params in debug mode
        if runtime.config.log_level.lower() == "debug":
            query_params = dict(request.query_params)
            full_url = f"{request.url.scheme}://{request.client.host}{request.url.path}"
            if query_params:
                full_url += f"?{request.url.query}"
            runtime.logger.debug(f"{full_url} [Worker {worker_pid}]")

        # Log based on status code
        if 400 <= response.status_code < 500:
            runtime.logger.warning(request.url.path)
        elif response.status_code >= 500:
            runtime.logger.error(request.url.path)
        else:
            runtime.logger.info(request.url.path)

    return response


# Set CORS middleware only for development. In prod env frontend and backend share the same origin,
# which negates strict CORS requirements as the browser handles requests under a unified origin
if runtime.mode == "dev":
    fast.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # dev environment: Local frontend
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            # mascope custom
            "Process-ID",
            # tus chunked uploads
            "Location",
            "Upload-Offset",
            "Tus-Resumable",
            "Tus-Version",
            "Tus-Extension",
            "Tus-Max-Size",
            "Upload-Expires",
            "Upload-Length",
        ],
    )

# routing
for router in routers:
    fast.include_router(router)


# exception handlers
@fast.exception_handler(RequestValidationError)
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
    try:
        body = await request.json()
    except Exception:
        body = None

    context_message = (
        f"Validation error on route {request.method} {request.url.path} "
        f"with body={body!r}"
    )
    runtime.logger.error(f"Validation error on {request.method} {request.url.path}")
    return handle_exception(exc, context_message, response_type="http")


@fast.exception_handler(ValueError)
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


@fast.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Custom exception handler for HTTPException instances. This handler captures HTTP exceptions
    like 403 Forbidden, 401 Unauthorized, and others, so they are processed in a unified format.

    :param request: The request object.
    :type request: Request
    :param exc: The HTTPException instance to be handled.
    :type exc: HTTPException
    :return: A JSONResponse with structured error information.
    :rtype: JSONResponse
    """
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        context_message = "Authorization failed"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        context_message = "Access denied"
    elif exc.status_code == status.HTTP_400_BAD_REQUEST:
        context_message = "Bad request"
    else:
        context_message = f"HTTPException on {request.method} {request.url.path} | detail={exc.detail}"
    return handle_exception(exc, context_message, response_type="http")


@fast.exception_handler(Exception)
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
    context_message = f"Unhandled exception on {request.method} {request.url.path}"
    # Handle the exception and get the response
    return handle_exception(exc, context_message, response_type="http")


async def init_app() -> None:
    """
    Initialize application components and perform startup system checks.

    This function orchestrates all initialization procedures that need
    to happen after database setup but before the app starts serving requests.
    """
    # Auto-create acquisition workspaces for all instruments
    await create_acquisition_workspaces()
