from fastapi import HTTPException
from sqlalchemy import asc, desc, func, select, delete, and_
from typing import List, Optional

from backend.db import async_session
from ..models.models import MatchInterference


async def get_match_interferences(
    target_isotope_id: Optional[str] = None,
    sample_item_id: Optional[str] = None,
    min_sample_peak_interference: float = None,
    max_sample_peak_interference: float = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 1000000,
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


async def delete_match_interferences(
    sample_item_ids: List[str], target_isotope_ids: Optional[List[str]] = None
):
    """
    Deletes match interferences for specified sample items, optionally filtered by target isotope IDs.

    This function deletes match interferences for a list of sample item IDs. If target isotope IDs are specified,
    only interferences corresponding to these isotopes are deleted.

    :param sample_item_ids: List of sample item IDs for which match interferences are to be deleted.
    :type sample_item_ids: List[str]
    :param target_isotope_ids: Optional list of target isotope IDs to filter match interferences, defaults to None
    :type target_isotope_ids: Optional[List[str]], optional
    """
    async with async_session() as session:
        query = delete(MatchInterference).where(
            MatchInterference.sample_item_id.in_(sample_item_ids)
        )

        if target_isotope_ids:
            query = query.where(
                MatchInterference.target_isotope_id.in_(target_isotope_ids)
            )

        await session.execute(query)
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
