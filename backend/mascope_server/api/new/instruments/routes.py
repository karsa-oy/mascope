from fastapi import APIRouter, Depends
from mascope_server.api.new.auth.dependencies import guest_user
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.new.instruments.service import get_instruments


instruments_router = APIRouter(prefix="/api/instruments", tags=["Instruments"])


@instruments_router.get("")
@api_route(status_code=200)
async def get_instruments_route(user=Depends(guest_user)):
    """Retrieve a list of available instruments.

    The function categorizes instruments into two currently supported types:
        - "orbi" for Orbitrap instruments
        - "tof" for Time-of-Flight (TOF) instruments

    :param user: The current authenticated user (guest or higher).
    :type user: User, optional
    :return: A dictionary containing the total count and a list of instruments with their types.
    :rtype: dict
    """
    return await get_instruments()
