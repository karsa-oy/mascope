from typing import Optional
from mascope_server.socket.server import sio
from mascope_server.db.models import User
from mascope_server.socket.emitter import event_emitter


@event_emitter.on("user.reload")
async def notify_clients_of_user_update(user: Optional[User] = None):
    """
    Handle user.reload events, emit socket events for user changes, optionally also to
    targeted to a specific user.

    :param user: The FastAPI users' user model
    """
    await sio.emit("user_reload_all", namespace="/")
    if user:
        await sio.emit("user_reload_me", room=f"user-{user.id}", namespace="/")
