import os

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from mascope_backend.api.new.auth.dependencies import guest_user
from mascope_backend.api.lib.api_features import api_route

from mascope_backend.runtime import runtime

temp_router = APIRouter(prefix="/api/temp", tags=["Temp", "Files"])


@temp_router.get("/{temp_file}")
@api_route(status_code=200)
async def get_temp_file_route(temp_file: str, user=Depends(guest_user)):
    """
    Download a temp file from the runtime env temp directory.
    Used for ephemeral files like export CSVs.

    :param temp_file: The temp file to download
    :type temp_file: str
    :param user: The current authenticated user (guest or higher).
    :type user: User, optional
    :return: A dictionary containing the total count and a list of instruments with their types.
    :rtype: dict
    """
    file_path = runtime.env.path("temp", temp_file)
    return FileResponse(file_path)
