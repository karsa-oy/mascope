from fastapi import HTTPException
from sqlalchemy import asc, desc, func, select, delete, and_
from typing import List, Optional

from backend.db_api_rest import async_session
from ..models.models import Match


async def get_matches(
    sample_item_id: Optional[str] = None,
    target_isotope_id: Optional[str] = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 1000000,
):
    async with async_session() as session:
        stmt = select(Match)

        if sample_item_id:
            stmt = stmt.filter(Match.sample_item_id == sample_item_id)

        if target_isotope_id:
            stmt = stmt.filter(Match.target_isotope_id == target_isotope_id)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(Match, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(Match, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        matches = result.scalars().all()

        return {
            "results": total,
            "data": [match.to_dict() for match in matches],
        }


async def get_match_by_id(match_id: str):
    async with async_session() as session:
        stmt = select(Match).filter(Match.match_id == match_id)
        result = await session.execute(stmt)
        match = result.scalars().first()

        if not match:
            raise HTTPException(
                status_code=404,
                detail=f"Match with ID {match_id} not found",
            )

        return match.to_dict()


async def delete_matches(
    sample_item_ids: List[str], target_isotope_ids: Optional[List[str]] = None
):
    """
    Deletes matches for specified sample items, optionally filtered by target isotope IDs.

    This function deletes matches for a list of sample item IDs. If target isotope IDs are provided,
    only matches corresponding to these isotopes are deleted.

    :param sample_item_ids: List of sample item IDs for which matches are to be deleted.
    :type sample_item_ids: List[str]
    :param target_isotope_ids: Optional list of target isotope IDs to filter matches, defaults to None
    :type target_isotope_ids: Optional[List[str]], optional
    """
    async with async_session() as session:
        query = delete(Match).where(Match.sample_item_id.in_(sample_item_ids))

        if target_isotope_ids:
            query = query.where(Match.target_isotope_id.in_(target_isotope_ids))

        await session.execute(query)
        await session.commit()


async def create_matches(match_isotope_df, sample_item_id):
    print("Saving matches to database")
    # Check for existing matches and save them
    async with async_session() as session:
        # Extract the required target_isotope_id values
        target_isotope_refs = match_isotope_df["target_isotope_id"].tolist()

        # Select matches that match the criteria
        stmt = select(Match.match_id).where(
            and_(
                Match.sample_item_id == sample_item_id,
                Match.target_isotope_id.in_(target_isotope_refs),
            )
        )

        result = await session.execute(stmt)
        matches = result.all()

        if matches:
            raise RuntimeError("Matches exist! Not going to overwrite")

        # Prepare the data for insertion
        match_isotope_for_insertion = [
            Match(
                **{
                    key: value
                    for key, value in record.items()
                    if key in Match.__table__.columns
                },
                sample_item_id=sample_item_id,
            )
            for record in match_isotope_df.to_dict(orient="records")
        ]

        # Insert the data
        session.add_all(match_isotope_for_insertion)

        # Commit the transaction to save the data
        await session.commit()
