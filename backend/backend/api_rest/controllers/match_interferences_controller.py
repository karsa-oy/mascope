from fastapi import HTTPException
from sqlalchemy import asc, desc, func, select, delete, and_
from backend.db_api_rest import async_session
from ..models.models import MatchInterference


async def get_match_interferences(
    target_isotope_id: str,
    sample_item_id: str,
    min_sample_peak_interference: float,
    max_sample_peak_interference: float,
    sort: str,
    order: str,
    page: int,
    limit: int,
):
    async with async_session() as session:
        stmt = select(MatchInterference)

        if target_isotope_id:
            stmt = stmt.filter(MatchInterference.target_isotope_id == target_isotope_id)

        if sample_item_id:
            stmt = stmt.filter(MatchInterference.sample_item_id == sample_item_id)

        if min_sample_peak_interference is not None:
            stmt = stmt.filter(
                MatchInterference.sample_peak_interference
                >= min_sample_peak_interference
            )

        if max_sample_peak_interference is not None:
            stmt = stmt.filter(
                MatchInterference.sample_peak_interference
                <= max_sample_peak_interference
            )

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(MatchInterference, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(MatchInterference, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        match_interferences = result.scalars().all()

        return {
            "results": total,
            "data": [
                match_interference.to_dict()
                for match_interference in match_interferences
            ],
        }


async def get_match_interference_by_id(match_interference_id: str):
    async with async_session() as session:
        stmt = select(MatchInterference).filter(
            MatchInterference.match_interference_id == match_interference_id
        )
        result = await session.execute(stmt)
        match_interference = result.scalars().first()

        if not match_interference:
            raise HTTPException(
                status_code=404,
                detail=f"MatchInterference with ID {match_interference_id} not found",
            )

        return match_interference.to_dict()


async def delete_match_interferences(sample_item_id: str):
    async with async_session() as session:
        await session.execute(
            delete(MatchInterference).where(
                MatchInterference.sample_item_id == sample_item_id
            )
        )
        await session.commit()


async def create_match_interferences(match_interference_df, sample_item_id):
    print("Saving match interferences to database")
    # Check for existing interferences and save them to database
    async with async_session() as session:
        # Extract the required target_isotope_id values
        target_isotope_refs = match_interference_df["target_isotope_id"].tolist()

        # Select interferences that match the criteria
        stmt = select(MatchInterference.match_interference_id).where(
            and_(
                MatchInterference.sample_item_id == sample_item_id,
                MatchInterference.target_isotope_id.in_(target_isotope_refs),
            )
        )

        result = await session.execute(stmt)
        match_interferences = result.all()

        if match_interferences:
            raise RuntimeError("Match interferences exist! Not going to overwrite")

        # Prepare the data for insertion
        match_interference_for_insertion = [
            MatchInterference(
                **{
                    key: value
                    for key, value in record.items()
                    if key in MatchInterference.__table__.columns
                },
                sample_item_id=sample_item_id,
            )
            for record in match_interference_df.to_dict(orient="records")
        ]

        # Insert the data
        session.add_all(match_interference_for_insertion)

        # Commit the transaction to save the data
        await session.commit()
