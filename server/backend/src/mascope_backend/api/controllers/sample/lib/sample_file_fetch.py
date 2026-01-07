from sqlalchemy import (
    select,
)

from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.db import SampleFile, async_session


async def fetch_sample_file(
    sample_file_id: str | None = None, filename: str | None = None
) -> SampleFile:
    """
    Retrieves a single sample file by its unique id or filename.

    param sample_file_id: The unique identifier of the sample file.
    :type sample_file_id: str | None
    :param filename: The filename of the sample file.
    :type filename: str | None

    :raises NotFoundException: If the sample file is not found.
    :return: The requested sample file's details.
    :rtype: SampleFile
    """
    # Validate input - exactly one parameter must be provided
    provided_params = sum(x is not None for x in [sample_file_id, filename])
    if provided_params != 1:
        raise ValueError("Exactly one of sample_file_id or filename must be provided")

    async with async_session() as session:
        # --- Fetch sample file provided parameter ---
        if sample_file_id:
            result = await session.execute(
                select(SampleFile).where(SampleFile.sample_file_id == sample_file_id)
            )
        else:
            result = await session.execute(
                select(SampleFile).where(SampleFile.filename == filename)
            )

        sample_file = result.scalar_one_or_none()

        # --- Check if sample file exists ---
        if not sample_file:
            raise NotFoundException(
                f"Sample file {sample_file_id or filename} not found"
            )

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
