from sqlalchemy import select

from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.db import SampleFile, async_session
from mascope_file.name import resolve_instrument_type


@api_controller()
async def get_instruments() -> dict:
    """
    Retrieve all instruments in the database, using the sample file table's instrument column.

    Steps:
    1. Query the database for distinct instrument names from the sample files.
    2. Resolve each instrument name to its type using the `resolve_instrument_type` function.
    3. Return the list of instruments and their resolved types along with the total count.

    :return: A dictionary containing:
        - message: A human-readable message summarizing the result.
        - results: The total number of distinct instruments.
        - data: A list of instruments with their names and resolved types.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Query distinct instrument names
        result = await session.execute(select(SampleFile.instrument).distinct())
        instruments = result.scalars().all()

        # Step 2: Resolve instrument types
        instrument_list = [
            i
            for i in [
                {
                    "instrument": instrument,
                    "type": resolve_instrument_type(instrument, throw=False),
                }
                for instrument in instruments
            ]
            if i["type"]  # filter out invalid instrument names
        ]

        # Step 3: Construct response
        return {
            "message": f"Retrieved {len(instrument_list)} instrument records",
            "results": len(instrument_list),
            "data": instrument_list,
        }
