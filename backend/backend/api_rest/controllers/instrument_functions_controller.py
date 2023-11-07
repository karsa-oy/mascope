import numpy as np

from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select
from backend.db_api_rest import async_session
from ..models.models import InstrumentFunction


# -------------------------------------------------------------------
# Main Logic Functions
# -------------------------------------------------------------------


async def read_instrument_functions(filename):
    instrument_functions = await get_instrument_function_by_filename(filename)

    peakshape = instrument_functions["peakshape"]
    R_p = instrument_functions["resolution_function"]
    if len(R_p) == 2:
        p1, p2 = R_p
        R = lambda m: m / (p1 * m + p2)
    elif len(R_p) == 3:
        R = np.poly1d(R_p)
    return peakshape, R


# -------------------------------------------------------------------
# Controller or Route Handlers
# -------------------------------------------------------------------


async def get_instrument_functions(
    instrument: str, sort: str, order: str, page: int, limit: int
):
    async with async_session() as session:
        stmt = select(InstrumentFunction)

        if instrument:
            stmt = stmt.filter(InstrumentFunction.instrument == instrument)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(InstrumentFunction, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(InstrumentFunction, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        instrument_functions = result.scalars().all()

        return {
            "results": total,
            "data": [
                instrument_function.to_dict()
                for instrument_function in instrument_functions
            ],
        }


async def get_instrument_function_by_id(instrument_function_id: str):
    async with async_session() as session:
        stmt = select(InstrumentFunction).filter(
            InstrumentFunction.instrument_function_id == instrument_function_id
        )
        result = await session.execute(stmt)
        instrument_function = result.scalars().first()

        if not instrument_function:
            raise HTTPException(
                status_code=404,
                detail=f"InstrumentFunction with ID {instrument_function_id} not found",
            )

        return instrument_function.to_dict()
