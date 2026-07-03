"""
FastAPI application with per-worker initialization.

This module defines the FastAPI application instance and its lifespan
context, which handles per-worker startup and shutdown tasks. The
lifespan runs once per worker process, after main process initialization
is complete.
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

    Each worker process runs this independently after the main process
    has completed initialization.

    Worker startup tasks:
    - Configure database engine and connection pool for this worker
    - Connect to Redis for cross-worker session storage

    Worker shutdown tasks:
    - Disconnect Redis client

    :param app: FastAPI application instance
    :raises ConnectionError: If Redis connection fails (logged as warning)
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
            f"Fast App startup: Redis storage client failed to connect:"
            f" {e} [Worker {worker_pid}]"
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


# Logging middleware
@fast.middleware("http")
async def logger_middleware(request: Request, call_next):
    worker_pid = os.getpid()

    # Make the request and receive a response
    response = await call_next(request)

    # add logging context
    client_host = request.client.host if request.client else "unknown"

    with runtime.logger.contextualize(
        path=request.url.path,
        method=request.method,
        client_host=client_host,
        request_id=str(uuid.uuid4()),
        status_code=response.status_code,
        worker_pid=worker_pid,
    ):
        # Log full URL with query params in debug mode
        if runtime.config.log_level == "debug":
            full_url = f"{request.url.scheme}://{client_host}{request.url.path}"
            if request.query_params:
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


# CORS only for dev — in prod, frontend and backend share the same origin
if runtime.mode == "dev":
    fast.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite dev server
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            # Mascope custom
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

# Routing
for router in routers:
    fast.include_router(router)


# Exception handlers
@fast.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors on incoming request data.

    :param request: The incoming request.
    :param exc: The validation error.
    :return: Structured JSON error response.
    :rtype: JSONResponse
    """
    # The request body is deliberately not included in the response or the
    # logs: it can carry credentials (e.g. login forms) and other user data.
    context_message = (
        f"Validation error on route {request.method} {request.url.path}"
    )
    return handle_exception(exc, context_message, response_type="http")


@fast.exception_handler(ValueError)
async def value_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
    """
    Handle ValueError — right type, inappropriate value.

    :param request: The incoming request.
    :param exc: The value error.
    :return: Structured JSON error response.
    :rtype: JSONResponse
    """
    return handle_exception(exc, "Invalid value", response_type="http")


@fast.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI HTTP exceptions (401, 403, 400, etc.) uniformly.

    :param request: The incoming request.
    :param exc: The HTTP exception.
    :return: Structured JSON error response.
    :rtype: JSONResponse
    """
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        context_message = "Authorization failed"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        context_message = "Access denied"
    elif exc.status_code == status.HTTP_400_BAD_REQUEST:
        context_message = "Bad request"
    else:
        context_message = (
            f"HTTPException on {request.method} {request.url.path}"
            f" | detail={exc.detail}"
        )
    return handle_exception(exc, context_message, response_type="http")


@fast.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for any unhandled exception during request processing.

    :param request: The incoming request.
    :param exc: The unhandled exception.
    :return: Structured JSON error response.
    :rtype: JSONResponse
    """
    context_message = f"Unhandled exception on {request.method} {request.url.path}"
    return handle_exception(exc, context_message, response_type="http")
