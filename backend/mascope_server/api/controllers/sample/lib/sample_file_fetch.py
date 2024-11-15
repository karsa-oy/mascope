from mascope_server.db import async_session
from mascope_server.db.models import SampleFile
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException

from sqlalchemy import (
    select,
)


async def fetch_sample_file(filename: str) -> dict:
    """
    Retrieves a single sample file by its unique filename.

    Steps:
    1. Execute a query to fetch the sample file with the specified filename.
    2. Check if the sample file exists. If not, raise a NotFoundException.
    3. Return the sample file's details as a dictionary.

    :param filename: Unique filename of the sample file to retrieve.
    :type filename: str
    :raises NotFoundException: If the sample file with the given filename is not found.
    :return: The requested sample file's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch sample file by ID
        result = await session.execute(
            select(SampleFile).where(SampleFile.filename == filename)
        )
        sample_file = result.scalar_one_or_none()
        # Step 2: Check existence
        if not sample_file:
            raise NotFoundException(f"Sample file with filename '{filename}' not found")

        # Step 3: Return sample file details
        return sample_file
