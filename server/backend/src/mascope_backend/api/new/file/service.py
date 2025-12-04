import shutil
import os
import datetime
from sqlalchemy import select

from mascope_file.name import parse_path_from_item_filename, get_instrument_type

from mascope_backend.db import async_session
from mascope_backend.db.models import SampleFile
from mascope_backend.api.lib.exceptions.api_exceptions import (
    NotFoundException,
    raise_api_warning,
)
from mascope_backend.api.lib.api_features import api_controller_background_task

from mascope_backend.runtime import runtime


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
)
async def download_files(
    sample_file_ids: list[str],
    independent_transaction: bool = False,
    sid=None,
    process_id=None,
    parent_id=None,
) -> dict:
    """
    Downloads sample files by their unique IDs and prepares them for client download.

    Steps:
    1. Fetch all sample files from the database using the provided IDs
    2. For multiple files, create a temporary directory and copy files there
    3. For a single file, copy it directly to the temp directory
    4. Create a zip archive for multiple files
    5. Return information about found and not found files

    :param sample_file_ids: List of IDs of the sample files to download
    :type sample_file_ids: list[str]
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction
    :type independent_transaction: bool, optional
    :param sid: Session ID for targeting specific clients when emitting events
    :type sid: str, optional
    :param process_id: Optional identifier for the processing task
    :type process_id: str, optional
    :param parent_id: Optional identifier of the parent task
    :type parent_id: str, optional
    :raises ApiException: If no downloadable files are found
    :return: A dictionary with information about found and not found files
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch sample file by ID
        sample_files = (
            (
                await session.execute(
                    select(SampleFile).where(
                        SampleFile.sample_file_id.in_(sample_file_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        if not sample_files:
            raise NotFoundException("No sample files found with the provided IDs")
    not_found = []
    found = []
    download = None
    if len(sample_files) > 1:
        # create a download folder using a datetime stamp
        datetime_stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        dirname = f"sample_files_{datetime_stamp}"
        download_dir = runtime.env.path("temp", dirname)
        os.mkdir(download_dir)
        # copy available files to the folder
        for sample_file in sample_files:
            # derive sample file path
            file_path = parse_path_from_item_filename(sample_file.filename)
            instrument_type = get_instrument_type(sample_file.filename)
            extension = "raw" if instrument_type == "orbi" else "h5"
            from_path = os.path.join(file_path, f"data.{extension}")
            # copy the sample file to the download folder
            if os.path.exists(from_path):
                to_path = os.path.join(
                    download_dir, f"{sample_file.filename}.{extension}"
                )
                shutil.copy(from_path, to_path)
                found.append(sample_file.to_dict())
            else:
                not_found.append(sample_file.to_dict())
        # zip the folder and set the zip as the download path
        if len(found) > 0:
            download = f"{dirname}.zip"
            zipfile_path = runtime.env.path("temp", dirname)
            shutil.make_archive(zipfile_path, "zip", download_dir)
    else:
        # derive sample file path
        sample_file = sample_files[0]
        file_path = parse_path_from_item_filename(sample_file.filename)
        instrument_type = get_instrument_type(sample_file.filename)
        extension = "raw" if instrument_type == "orbi" else "h5"
        from_path = os.path.join(file_path, f"data.{extension}")
        # copy the sample file to the temp folder
        if os.path.exists(from_path):
            download = f"{sample_file.filename}.{extension}"
            to_path = runtime.env.path("temp", download)
            if os.path.exists(to_path):
                os.remove(to_path)
            shutil.copy(from_path, to_path)
            found.append(sample_file.to_dict())
        else:
            not_found.append(sample_file.to_dict())

    files_found = (
        f"retrieved {len(found)} file{'s' if len(found) > 1 else ''}" if found else None
    )
    files_not_found = (
        f"skipped {len(not_found)} file{'s' if len(not_found) > 1 else ''} which could not be found: {', '.join([f['filename'] for f in not_found])}"
        if not_found
        else None
    )
    message = "File download: " + " and ".join(
        [m for m in [files_found, files_not_found] if m]
    )

    if not_found:
        runtime.logger.warning(message)
        raise_api_warning(
            message,
            {
                "data": {
                    "download": download,
                    "found": [f["filename"] for f in found],
                    "not_found": [f["filename"] for f in not_found],
                }
            },
        )
    else:
        runtime.logger.info(message)
        return {
            "message": message,
            "data": {
                "found": found,
                "not_found": not_found,
            },
            "_notification_data": {
                "download": download,
            },
        }
