from fastapi import APIRouter, Depends, BackgroundTasks, Request

from mascope_backend.db.id import gen_id

from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.new.auth.dependencies import guest_user

from mascope_backend.api.new.file.schema import FileDownloadBody
from mascope_backend.api.new.file.service import download_files


file_router = APIRouter(prefix="/api/file", tags=["Parameters"])


@file_router.post("/download")
@api_route(status_code=202)
async def download_file_route(
    request: Request,
    body: FileDownloadBody,
    background_tasks: BackgroundTasks,
    user=Depends(guest_user),
):
    """Download one or more sample files if available

    :param body: the request body
    :type body: FileDownloadBody
    :param user: The authenticated user, defaults to Depends(guest_user).
    :return: Dictionary containing a message and the parameters.
    """

    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        download_files,
        sample_file_ids=body.sample_file_ids,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": "Downloading sample files, please wait.",
        "process_id": process_id,
    }
