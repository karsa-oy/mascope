# Import this here to avoid "free(): invalid pointer" error on Linux
from mascope_hardware.tofwerk.lib.TwTool import *

import os
import socketio
import uvicorn

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
from mascope_server.api_sio import sio
from mascope_server.db import init_db
from mascope_server.api.exceptions import handle_exception

from mascope_server.api.routes.sample_items_routes import sample_items_router
from mascope_server.api.routes.sample_batches_routes import sample_batches_router
from mascope_server.api.routes.workspace_routes import workspace_router
from mascope_server.api.routes.sample_files_routes import sample_files_router
from mascope_server.api.routes.calibration_routes import calibration_router
from mascope_server.api.routes.match_isotopes_routes import match_isotopes_router
from mascope_server.api.routes.match_ions_routes import match_ions_router
from mascope_server.api.routes.match_compounds_routes import match_compounds_router
from mascope_server.api.routes.match_collections_routes import match_collections_router
from mascope_server.api.routes.match_samples_routes import match_samples_router
from mascope_server.api.routes.target_collections_routes import (
    target_collections_router,
)
from mascope_server.api.routes.target_collection_in_sample_batch_routes import (
    target_collection_in_sample_batch_router,
)
from mascope_server.api.routes.target_compounds_routes import target_compounds_router
from mascope_server.api.routes.target_compound_in_target_collection_routes import (
    target_compound_in_target_collection_router,
)
from mascope_server.api.routes.target_ions_routes import target_ions_router
from mascope_server.api.routes.ionization_mechanisms_routes import (
    ionization_mechanisms_router,
)
from mascope_server.api.routes.target_isotopes_routes import target_isotopes_router
from mascope_server.api.routes.match_interferences_routes import (
    match_interferences_router,
)
from mascope_server.api.routes.instrument_functions_routes import (
    instrument_functions_router,
)
from mascope_server.api.routes.attribute_templates_routes import (
    attribute_templates_router,
)
from mascope_server.api.routes.visualization_routes import visualization_router
from mascope_server.api.routes.match_routes import match_router
from mascope_server.api.routes.match_aggregate_routes import match_aggreagate_router
from mascope_server.api.routes.match_rating_routes import match_rating_router
from mascope_server.api.routes.samples_routes import samples_router


load_dotenv()

api_port = int(os.environ.get("MASCOPE_PUBLIC_API_PORT"))
mode = os.environ.get("MASCOPE_PUBLIC_MODE")

fastapi_app = FastAPI()


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


routers = [
    sample_items_router,
    sample_batches_router,
    workspace_router,
    sample_files_router,
    calibration_router,
    match_rating_router,
    match_router,
    match_aggreagate_router,
    match_interferences_router,
    match_isotopes_router,
    match_ions_router,
    match_compounds_router,
    match_collections_router,
    match_samples_router,
    target_collections_router,
    target_collection_in_sample_batch_router,
    target_compounds_router,
    target_compound_in_target_collection_router,
    target_ions_router,
    ionization_mechanisms_router,
    target_isotopes_router,
    instrument_functions_router,
    attribute_templates_router,
    visualization_router,
    samples_router,
]

for router in routers:
    fastapi_app.include_router(router)

# Initialize ASGI app with socket.io and FastAPI app
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)


def run():
    """Entry point to run Mascope server"""
    uvicorn.run(
        "mascope_server.main:app",
        host="0.0.0.0" if mode == "development" else "127.0.0.1",
        port=api_port,
        reload=(mode == "development"),
    )


if __name__ == "__main__":
    run()
