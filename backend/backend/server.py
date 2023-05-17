import socketio
from fastapi import FastAPI
from backend.db import run as run_db
from .db_api_rest import init_db
from .api_rest.routes.sample_items_routes import sample_items_router
from .api_rest.routes.sample_batches_routes import sample_batches_router

# Configure socket.io server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_timeout=60,
    logger=True,
)

fastapi_app = FastAPI()


@fastapi_app.on_event("startup")
async def startup_event():
    await init_db()
    run_db()


fastapi_app.include_router(sample_items_router)
fastapi_app.include_router(sample_batches_router)

# Initialize ASGI app with socket.io and FastAPI app
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
