from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.new.auth.dependencies import guest_user

from .service import get_params

params_router = APIRouter(prefix="/api/params", tags=["Parameters"])


@params_router.get("")
@api_route()
async def get_params_route(user=Depends(guest_user)):
    """Retrieve parameters.

    :param user: The authenticated user, defaults to Depends(guest_user).
    :return: Dictionary containing a message and the parameters.
    """
    return await get_params()
