from mascope_backend.db import async_session
from mascope_backend.db.models import SampleFile
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException

from sqlalchemy import (
    select,
)


async def fetch_sample_file(filename: str) -> SampleFile:
    """
    Retrieves a single sample file by its unique filename.

    Steps:
    - Execute a query to fetch the sample file by the filename.
    - If the sample file is not found, raise a NotFoundException.
    - Return the sample file's details.

    :param filename: Unique filename of the sample file to retrieve.
    :type filename: str
    :raises NotFoundException: If the sample file with the specified filename is not found.
    :return: The requested sample file's details.
    :rtype: SampleFile
    """
    async with async_session() as session:
        # --- Fetch sample file by filename ---
        result = await session.execute(
            select(SampleFile).where(SampleFile.filename == filename)
        )
        sample_file = result.scalar_one_or_none()
        # --- Check if sample file exists ---
        if not sample_file:
            raise NotFoundException(f"Sample file with filename '{filename}' not found")

        # --- Return sample file details ---
        return sample_file


async def fetch_sample_files(filenames: list[str] | None = None) -> dict:
    """
    Retrieves a multiple sample files from a list of filenames. If no filenames are provided,
    all sample files are retrieved.

    Steps:
    1. Execute a query to fetch the sample files with the specified filenames.
    2. Return the sample file's details as a dictionary.

    :param filenames: List of filenames of the sample files to retrieve.
    :type filenames: list[str]
    :return: The requested sample file's details.
    :rtype: dict
    """
    async with async_session() as session:
        if filenames is None:
            # Return all sample file records
            result = await session.execute(select(SampleFile))
        else:
            result = await session.execute(
                select(SampleFile).where(SampleFile.filename.in_(filenames))
            )
        sample_files = result.scalars().all()
    return sample_files
