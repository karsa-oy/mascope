import os

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.api.new.auth.dependencies import guest_user
from mascope_backend.api.new.temp.storage import user_temp_path


temp_router = APIRouter(prefix="/api/temp", tags=["Temp", "Files"])


@temp_router.get("/{temp_file}")
@api_route(status_code=200)
async def get_temp_file_route(temp_file: str, user=Depends(guest_user)):
    """
    Download an ephemeral temp file belonging to the current user.

    Temp files (export CSVs, peak data, download bundles) are scoped to the
    requesting user's own directory, so a user can only download files they
    generated - never another user's, even by guessing the filename. Path
    traversal is rejected by ``user_temp_path``.

    :param temp_file: The temp file to download.
    :type temp_file: str
    :param user: The current authenticated user (guest or higher).
    :type user: User, optional
    :return: The requested file.
    :rtype: FileResponse
    """
    try:
        # create=False: reading must not mint empty per-user directories.
        file_path = user_temp_path(user.id, temp_file, create=False)
    except ValueError as e:
        raise NotFoundException("File not found") from e
    if not os.path.isfile(file_path):
        raise NotFoundException("File not found")
    return FileResponse(file_path, filename=os.path.basename(temp_file))
