"""
FastAPI application with per-worker initialization.

This module defines the FastAPI application instance and its lifespan context,
which handles per-worker startup and shutdown tasks. The lifespan runs once
per worker process, after main process initialization is complete.
"""

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mascope_backend.api.lib.exceptions.api_exceptions import handle_exception
from mascope_backend.api.routes import routers
from mascope_backend.db import init_db
from mascope_backend.runtime import runtime
from mascope_backend.socket.storage import redis_storage_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Per-worker lifespan context manager for FastAPI application.

    This context manager handles worker-specific startup and shutdown tasks.
    Each worker process runs this independently after the main process has
    completed initialization.

    Worker startup tasks:
    - Configure database engine and connection pool for this worker
    - Connect to Redis for cross-worker session storage

    Worker shutdown tasks:
    - Disconnect Redis client

    :param app: FastAPI application instance
    :raises ConnectionError: If Redis connection fails (non-fatal, logged as warning)
    """
    worker_pid = os.getpid()

    # --- STARTUP TASKS ---
    runtime.logger.info(
        f"Fast App startup: starting initialization [Worker {worker_pid}]"
    )
    # Initialize database
    runtime.logger.info(
        f"Fast App startup: initializing database [Worker {worker_pid}]"
    )
    await init_db()

    # Initialize Redis storage client for cross-worker socket state
    runtime.logger.info(
        f"Fast App startup: connecting Redis storage client [Worker {worker_pid}]"
    )
    try:
        await redis_storage_client.connect()
    except ConnectionError as e:
        runtime.logger.error(
            f"Fast App startup: Redis storage client failed to connect: {e} [Worker {worker_pid}]"
        )
        runtime.logger.warning("Multi-worker storage sharing will not work")

    # Yield control back to FastAPI
    yield

    # --- SHUTDOWN TASKS ---
    runtime.logger.info(
        f"Fast App shutdown: closing Redis storage client [Worker {worker_pid}]"
    )
    await redis_storage_client.disconnect()


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
