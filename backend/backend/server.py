import socketio
from fastapi import FastAPI

from .socket_events import sio
from fastapi.middleware.cors import CORSMiddleware
from backend.db import run as run_db
from .db_api_rest import init_db
from .api_rest.routes.sample_items_routes import sample_items_router
from .api_rest.routes.sample_batches_routes import sample_batches_router
from .api_rest.routes.workspace_routes import workspace_router
from .api_rest.routes.sample_files_routes import sample_files_router
from .api_rest.routes.calibration_routes import calibration_router
from .api_rest.routes.matches_routes import matches_router
from .api_rest.routes.target_collections_routes import target_collections_router
from .api_rest.routes.target_collection_in_sample_batch_routes import (
    target_collection_in_sample_batch_router,
)
from .api_rest.routes.target_compounds_routes import target_compounds_router
from .api_rest.routes.target_compound_in_target_collection_routes import (
    target_compound_in_target_collection_router,
)
from .api_rest.routes.target_ions_routes import target_ions_router
from .api_rest.routes.ionization_mechanisms_routes import ionization_mechanisms_router
from .api_rest.routes.target_isotopes_routes import target_isotopes_router
from .api_rest.routes.match_interferences_routes import match_interferences_router
from .api_rest.routes.instrument_functions_routes import instrument_functions_router
from .api_rest.routes.attribute_templates_routes import attribute_templates_router


fastapi_app = FastAPI()


@fastapi_app.on_event("startup")
async def startup_event():
    await init_db()
    run_db()


# CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

routers = [
    sample_items_router,
    sample_batches_router,
    workspace_router,
    sample_files_router,
    calibration_router,
    matches_router,
    target_collections_router,
    target_collection_in_sample_batch_router,
    target_compounds_router,
    target_compound_in_target_collection_router,
    target_ions_router,
    ionization_mechanisms_router,
    target_isotopes_router,
    match_interferences_router,
    instrument_functions_router,
    attribute_templates_router,
]

for router in routers:
    fastapi_app.include_router(router)

# Initialize ASGI app with socket.io and FastAPI app
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
