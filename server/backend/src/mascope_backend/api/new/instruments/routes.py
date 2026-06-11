from fastapi import APIRouter, Depends

from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.new.auth.dependencies import guest_user
from mascope_backend.api.new.instruments.service import get_instruments
from mascope_backend.api.new.workspaces.dependencies import (
    accessible_acquisition_instruments,
)


instruments_router = APIRouter(prefix="/api/instruments", tags=["Instruments"])


@instruments_router.get("")
@api_route(status_code=200)
async def get_instruments_route(user=Depends(guest_user)):
    """Retrieve a list of available instruments.

    Each instrument includes a ``disabled`` flag indicating whether the
    current user lacks access to that instrument's acquisition workspace.

    :param user: The current authenticated user.
    :return: A dictionary containing the total count and a list of instruments with their types.
    """
    result = await get_instruments()
    allowed = await accessible_acquisition_instruments(user)

    if allowed is not None:
        for item in result["data"]:
            item["disabled"] = item["instrument"] not in allowed
    else:
        for item in result["data"]:
            item["disabled"] = False

    return result
