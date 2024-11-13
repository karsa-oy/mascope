from sqlalchemy import select
from mascope_server.db import async_session
from mascope_server.db.models import SampleFile
from mascope_server.api.lib.api_features import api_controller
from mascope_lib.instrument import resolve_instrument_type


@api_controller()
async def get_instruments():
    """
    Retrieve all instruments in the database, using the sample file table's instrument column.

    :return: A list of instruments.
    """
    async with async_session() as session:
        instruments = [
            {"instrument": i[0], "type": resolve_instrument_type(i[0])}
            for i in (
                (await session.execute(select(SampleFile.instrument).distinct()))
                .columns(SampleFile.instrument)
                .all()
            )
        ]
        return {
            "results": len(instruments),
            "data": instruments,
            "message": f"Retrieved {len(instruments)} instrument records",
        }
