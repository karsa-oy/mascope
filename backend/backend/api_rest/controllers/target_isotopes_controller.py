from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select
from backend.db_api_rest import async_session
from ..models.models import TargetIsotope


async def get_target_isotopes(
    target_ion_id: str,
    min_mz: float,
    max_mz: float,
    min_relative_abundance: float,
    max_relative_abundance: float,
    sort: str,
    order: str,
    page: int,
    limit: int,
):
    async with async_session() as session:
        stmt = select(TargetIsotope)

        if target_ion_id:
            stmt = stmt.filter(TargetIsotope.target_ion_id == target_ion_id)

        if min_mz is not None:
            stmt = stmt.filter(TargetIsotope.mz >= min_mz)

        if max_mz is not None:
            stmt = stmt.filter(TargetIsotope.mz <= max_mz)

        if min_relative_abundance is not None:
            stmt = stmt.filter(
                TargetIsotope.relative_abundance >= min_relative_abundance
            )

        if max_relative_abundance is not None:
            stmt = stmt.filter(
                TargetIsotope.relative_abundance <= max_relative_abundance
            )

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetIsotope, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetIsotope, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        target_isotopes = result.scalars().all()

        return {
            "results": total,
            "data": [target_isotope.to_dict() for target_isotope in target_isotopes],
        }


async def get_target_isotope_by_id(target_isotope_id: str):
    async with async_session() as session:
        stmt = select(TargetIsotope).filter(
            TargetIsotope.target_isotope_id == target_isotope_id
        )
        result = await session.execute(stmt)
        target_isotope = result.scalars().first()

        if not target_isotope:
            raise HTTPException(
                status_code=404,
                detail=f"TargetIsotope with ID {target_isotope_id} not found",
            )

        return target_isotope.to_dict()
