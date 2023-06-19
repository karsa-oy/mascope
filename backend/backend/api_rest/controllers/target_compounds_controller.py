from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select

from backend.db_api_rest import async_session
from ..models.models import TargetCompound


async def get_target_compounds(
    target_compound_name: str,
    target_compound_formula: str,
    sort: str,
    order: str,
    page: int,
    limit: int,
):
    async with async_session() as session:
        stmt = select(TargetCompound)

        if target_compound_name:
            stmt = stmt.filter(
                TargetCompound.target_compound_name == target_compound_name
            )

        if target_compound_formula:
            stmt = stmt.filter(
                TargetCompound.target_compound_formula == target_compound_formula
            )

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetCompound, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetCompound, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        target_compounds = result.scalars().all()

        return {
            "results": total,
            "data": [target_compound.to_dict() for target_compound in target_compounds],
        }


async def get_target_compound_by_id(target_compound_id: str):
    async with async_session() as session:
        stmt = select(TargetCompound).filter(
            TargetCompound.target_compound_id == target_compound_id
        )
        result = await session.execute(stmt)
        target_compound = result.scalars().first()

        if not target_compound:
            raise HTTPException(
                status_code=404,
                detail=f"TargetCompound with ID {target_compound_id} not found",
            )

        return target_compound.to_dict()
