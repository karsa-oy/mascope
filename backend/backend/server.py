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


fastapi_app = FastAPI()


@fastapi_app.on_event("startup")
async def startup_event():
    await init_db()
    run_db()


# CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:8080"],  # Allow specific origins
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.include_router(sample_items_router)
fastapi_app.include_router(sample_batches_router)
fastapi_app.include_router(workspace_router)
fastapi_app.include_router(sample_files_router)
fastapi_app.include_router(calibration_router)

# Initialize ASGI app with socket.io and FastAPI app
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
