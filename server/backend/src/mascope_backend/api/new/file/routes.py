from fastapi import APIRouter, BackgroundTasks, Depends

from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.new.auth.dependencies import current_active_user
from mascope_backend.api.new.file.schema import FileDownloadBody
from mascope_backend.api.new.file.service import download_files
from mascope_backend.api.new.workspaces.dependencies import (
    check_sample_file_access_bulk,
)
from mascope_backend.db import User
from mascope_backend.db.id import gen_id


file_router = APIRouter(prefix="/api/file", tags=["Parameters"])


@file_router.post("/download")
@api_route(status_code=202)
async def download_file_route(
    body: FileDownloadBody,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_active_user),
):
    """Download one or more sample files if available.

    Checks that the user has guest-level access to at least one sample item
    referencing each requested file, via workspace membership.

    :param body: The request body containing sample file IDs to download.
    :type body: FileDownloadBody
    :param user: The authenticated user.
    :return: Dictionary containing a message and the process ID.
    """
    await check_sample_file_access_bulk(body.sample_file_ids, user, "guest")

    process_id = gen_id(8)

    background_tasks.add_task(
        download_files,
        sample_file_ids=body.sample_file_ids,
        independent_transaction=True,
        user_id=user.id,
        process_id=process_id,
    )
    return {
        "message": "Downloading sample files, please wait.",
        "process_id": process_id,
    }
