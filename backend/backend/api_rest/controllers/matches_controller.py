import pandas as pd
from sqlalchemy import asc, desc, func, select, delete, and_
from typing import List, Optional
from backend.db_api_rest import async_session
from ..utils.api_features import api_controller
from ..exceptions import NotFoundException
from ..models.models import Match


@api_controller()
async def get_matches(
    sample_item_id: Optional[str] = None,
    target_isotope_id: Optional[str] = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 1000000,
) -> dict:
    """
    Retrieves a paginated list of matches, optionally filtered by sample item ID and target isotope ID, and sorted by a specified column.

    Steps:
    1. Construct a SQLAlchemy query to select all matches.
    2. Apply filtering based on provided parameters.
    3. Apply sorting based on the provided sort and order parameters.
    4. Apply pagination based on the provided page and limit parameters.
    5. Execute the query and fetch the results.
    6. Convert the results into a list of dictionaries for JSON serialization.

    :param sample_item_id: Filter by sample item ID, defaults to None.
    :type sample_item_id: Optional[str], optional
    :param target_isotope_id: Filter by target isotope ID, defaults to None.
    :type target_isotope_id: Optional[str], optional
    :param sort: Column to sort by, defaults to None.
    :type sort: str, optional
    :param order: Sorting order, defaults to None.
    :type order: str, optional
    :param page: Page number for pagination, defaults to 0.
    :type page: int, optional
    :param limit: Number of items per page, defaults to a large number.
    :type limit: int, optional
    :return: A dictionary with the total count and a list of matches.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct a SQLAlchemy query to select all matches.
        stmt = select(Match)

        # Step 2: Apply filters if specified
        if sample_item_id:
            stmt = stmt.filter(Match.sample_item_id == sample_item_id)
        if target_isotope_id:
            stmt = stmt.filter(Match.target_isotope_id == target_isotope_id)

        # Step 3: Apply sorting
        if sort:
            sort_expression = (
                desc(getattr(Match, sort))
                if order == "desc"
                else asc(getattr(Match, sort))
            )
            stmt = stmt.order_by(sort_expression)

        # Step 4: Apply pagination
        total = await session.scalar(select(func.count()).select_from(stmt))
        stmt = stmt.offset(page * limit).limit(limit)

        # Step 5: Execute query
        result = await session.execute(stmt)
        matches = result.scalars().all()

        # Step 6: Return results
        return {"results": total, "data": [match.to_dict() for match in matches]}


@api_controller()
async def get_match(match_id: str) -> dict:
    """
    Retrieves a single match by its unique ID.

    Steps:
    1. Execute a query to fetch the match with the specified ID.
    2. Check if the match exists. If not, raise a NotFoundException.
    3. Return the match's details as a dictionary.

    :param match_id: Unique identifier of the match to retrieve.
    :type match_id: str
    :return: The requested match's details.
    :rtype: dict
    :raises NotFoundException: If the match with the given ID is not found.
    """
    async with async_session() as session:
        # Step 1: Fetch match by ID
        match = await session.get(Match, match_id)

        # Step 2: Check existence
        if not match:
            raise NotFoundException(f"Match with ID '{match_id}' not found")

        # Step 3: Return match details
        return match.to_dict()


@api_controller()
async def delete_matches(
    sample_item_ids: List[str], target_isotope_ids: Optional[List[str]] = None
):
    """
    Deletes matches for specified sample items, optionally filtered by target isotope IDs.
    This operation supports batch deletion and can be restricted to specific isotopes if needed.

    Steps:
    1. Start a new database session and construct a delete query for matches based on sample item IDs.
    2. If target isotope IDs are provided, apply an additional filter to restrict the deletion to those isotopes.
    3. Execute the delete query and commit the transaction to finalize the deletion.

    :param sample_item_ids: List of sample item IDs for which matches are to be deleted.
    :type sample_item_ids: List[str]
    :param target_isotope_ids: Optional list of target isotope IDs to further filter the matches to be deleted.
    :type target_isotope_ids: Optional[List[str]]
    """
    async with async_session() as session:
        query = delete(Match).where(Match.sample_item_id.in_(sample_item_ids))
        if target_isotope_ids:
            query = query.where(Match.target_isotope_id.in_(target_isotope_ids))
        await session.execute(query)
        await session.commit()


@api_controller()
async def create_matches(match_isotope_df: pd.DataFrame, sample_item_id: str):
    """
    Creates matches for a given sample item based on the provided DataFrame of isotopes.

    This function checks for existing matches for the given sample item and isotopes to avoid duplications.
    New matches are then created and saved to the database.

    Steps:
    1. Start a new database session and construct a query to check for existing matches for the sample item and isotopes.
    2. If existing matches are found, raise a RuntimeError to prevent overwriting.
    3. Prepare the data for insertion based on the provided DataFrame.
    4. Insert the new matches into the database and commit the transaction.

    :param match_isotope_df: DataFrame containing isotope data for creating matches.
    :type match_isotope_df: pd.DataFrame
    :param sample_item_id: ID of the sample item for which matches are being created.
    :type sample_item_id: str
    :raises RuntimeError: If matches already exist for the given sample item and isotopes.
    """
    print("Saving matches to database")
    # Step 1: Check for existing matches for the sample item and isotopes
    async with async_session() as session:
        # Extract the required target_isotope_id values
        target_isotope_refs = match_isotope_df["target_isotope_id"].tolist()
        stmt = select(Match.match_id).where(
            and_(
                Match.sample_item_id == sample_item_id,
                Match.target_isotope_id.in_(target_isotope_refs),
            )
        )
        result = await session.execute(stmt)
        matches = result.all()
        # Step 2: If existing matches are found, raise a RuntimeError to prevent overwriting.
        if matches:
            raise RuntimeError(
                "Matches already exist for the given sample item and isotopes."
            )

        # Step 3: Prepare the data for insertion based on the provided DataFrame.
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
        # Step 4: Insert the new matches into the database and commit the transaction.
        session.add_all(match_isotope_for_insertion)
        await session.commit()
