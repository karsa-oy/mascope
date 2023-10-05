from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select

from backend.db_api_rest import async_session
from ..models.models import TargetIon


async def get_target_ions(
    target_compound_id: str,
    ionization_mechanism_id: str,
    target_ion_formula: str,
    sort: str,
    order: str,
    page: int,
    limit: int,
):
    async with async_session() as session:
        stmt = select(TargetIon)

        if target_compound_id:
            stmt = stmt.filter(TargetIon.target_compound_id == target_compound_id)

        if ionization_mechanism_id:
            stmt = stmt.filter(
                TargetIon.ionization_mechanism_id == ionization_mechanism_id
            )

        if target_ion_formula:
            stmt = stmt.filter(TargetIon.target_ion_formula == target_ion_formula)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetIon, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetIon, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        target_ions = result.scalars().all()

        return {
            "results": total,
            "data": [target_ion.to_dict() for target_ion in target_ions],
        }


async def get_target_ion_by_id(target_ion_id: str):
    async with async_session() as session:
        stmt = select(TargetIon).filter(TargetIon.target_ion_id == target_ion_id)
        result = await session.execute(stmt)
        target_ion = result.scalars().first()

        if not target_ion:
            raise HTTPException(
                status_code=404,
                detail=f"TargetIon with ID {target_ion_id} not found",
            )

        return target_ion.to_dict()
