from sqlalchemy import asc, desc, func, select, delete, and_
from typing import List, Optional
from mascope_server.db import async_session
from mascope_server.api.utils.api_features import api_controller
from mascope_server.api.exceptions import NotFoundException, DuplicateException
from mascope_server.api.controllers.match.util import fetch_sample_item_ids
from mascope_server.api.models.models import (
    MatchInterference,
)
from mascope_server.api.models.pydantic_models.match_interferences_pydantic_model import (
    MatchInterferenceBase,
)


@api_controller()
async def get_match_interferences(
    target_isotope_id: Optional[str] = None,
    sample_item_id: Optional[str] = None,
    min_sample_peak_interference: Optional[float] = None,
    max_sample_peak_interference: Optional[float] = None,
    sort: Optional[str] = None,
    order: Optional[str] = None,
    page: int = 0,
    limit: int = 1000000,
) -> dict:
    """
    Retrieves a paginated list of match interferences, optionally filtered by various criteria, and sorted by a specified column.

    Steps:
    1. Construct a SQLAlchemy query to select all match interferences.
    2. Apply filtering based on provided parameters (target isotope ID, sample item ID, and sample peak interference range).
    3. Apply sorting based on the provided sort and order parameters.
    4. Apply pagination based on the provided page and limit parameters.
    5. Execute the query and fetch the results.
    6. Convert the results into a list of dictionaries for JSON serialization.

    :param target_isotope_id: Filter by target isotope ID, defaults to None.
    :type target_isotope_id: Optional[str], optional
    :param sample_item_id: Filter by sample item ID, defaults to None.
    :type sample_item_id: Optional[str], optional
    :param min_sample_peak_interference: Minimum sample peak interference value for filtering, defaults to None.
    :type min_sample_peak_interference: Optional[float], optional
    :param max_sample_peak_interference: Maximum sample peak interference value for filtering, defaults to None.
    :type max_sample_peak_interference: Optional[float], optional
    :param sort: Column to sort by, defaults to None.
    :type sort: Optional[str], optional
    :param order: Sorting order, 'asc' for ascending or 'desc' for descending, defaults to None.
    :type order: Optional[str], optional
    :param page: Page number for pagination, defaults to 0.
    :type page: int, optional
    :param limit: Number of items per page, defaults to 100.
    :type limit: int, optional
    :return: A dictionary containing the total count and a list of match interferences.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct a SQLAlchemy query to select all match interferences.
        stmt = select(MatchInterference)

        # Step 2: Apply filters based on parameters
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

        # Step 3: Apply sorting
        if sort:
            sort_expression = (
                desc(getattr(MatchInterference, sort))
                if order == "desc"
                else asc(getattr(MatchInterference, sort))
            )
            stmt = stmt.order_by(sort_expression)

        # Step 4: Apply pagination
        total = await session.scalar(
            select(func.count()).select_from(stmt)  # pylint: disable=not-callable
        )
        stmt = stmt.offset(page * limit).limit(limit)

        # Step 5: Execute the query and return results
        result = await session.execute(stmt)
    match_interferences = result.scalars().all()

    # Step 6: Return results
    return {
        "results": total,
        "data": [
            match_interference.to_dict() for match_interference in match_interferences
        ],
    }


@api_controller()
async def get_match_interference(match_interference_id: str) -> dict:
    """
    Retrieves a single match interference by its unique ID.

    Steps:
    1. Execute a query to fetch the match interference with the specified ID.
    2. Check if the match interference exists. If not, raise a NotFoundException.
    3. Return the match interference's details as a dictionary.

    :param match_interference_id: Unique identifier of the match interference to retrieve.
    :type match_interference_id: str
    :raises NotFoundException: If the match interference with the given ID is not found.
    :return: The requested match interference's details.
    :rtype: dict
    """
    async with async_session() as session:
        match_interference = await session.get(MatchInterference, match_interference_id)
    if not match_interference:
        raise NotFoundException(
            f"Match interference with ID '{match_interference_id}' not found"
        )
    return match_interference.to_dict()


@api_controller()
async def delete_match_interferences(
    sample_item_id: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    target_isotope_ids: Optional[List[str]] = None,
) -> dict:
    """
    Deletes match interferences for specified sample items, optionally filtered by target isotope IDs.
    This operation supports deletion by either a single sample item ID, a batch of sample items from a sample batch,
    or can be restricted to specific isotopes if target isotope IDs are provided.

    Steps:
    1. Validate the input to ensure that either a sample item ID or a sample batch ID is provided.
    2. If a sample batch ID is provided, fetch the associated sample item IDs.
    3. Construct and execute a delete query for match interferences based on the resolved sample item IDs.
       Apply an additional filter to restrict the deletion to specific target isotopes if these IDs are provided.
    4. Commit the transaction and report the number of deleted records.

    :param sample_item_id: ID of the single sample item for which match interferences are to be deleted, optional.
    :type sample_item_id: Optional[str]
    :param sample_batch_id: ID of the sample batch from which sample items are derived for deletion, optional.
    :type sample_batch_id: Optional[str]
    :param target_isotope_ids: Optional list of target isotope IDs to further filter the match interferences to be deleted.
    :type target_isotope_ids: Optional[List[str]]
    :return: A message with the outcome of the deletion process including the count of deleted records.
    :rtype: dict
    """
    sample_item_ids, sample_ref = await fetch_sample_item_ids(
        sample_item_id, sample_batch_id
    )

    async with async_session() as session:
        query = delete(MatchInterference).where(
            MatchInterference.sample_item_id.in_(sample_item_ids)
        )
        if target_isotope_ids:
            query = query.where(
                MatchInterference.target_isotope_id.in_(target_isotope_ids)
            )
        result = await session.execute(query)
        await session.commit()
        deleted_count = result.rowcount

    message = f"{deleted_count} match interference{'s' if deleted_count != 1 else ''} deleted for {sample_ref}."
    if target_isotope_ids:
        message += f" Limited by {len(target_isotope_ids)} specified target isotope{'s' if len(target_isotope_ids) != 1 else ''}."

    print(message)
    return {"message": message}


@api_controller()
async def create_match_interferences(
    match_interferences: List[MatchInterferenceBase],
    independent_transaction: bool = False,
):
    """
    Creates match interferences for a given sample item based on the provided match interference data.

    Steps:
    1. Check for existing match interferences to avoid duplication.
    2. Insert the new match interferences into the database and commit the transaction.
    3. Refresh and return the created match interferences.

    :param match_interferences: List of interference data for creating match interferences.
    :type match_interferences: List[MatchInterferenceBase]
    :param independent_transaction: Indicates if the operation should be independent of any ongoing transactions, defaults to False.
    :type independent_transaction: bool, optional
    :return: The created match interferences data.
    :rtype: dict
    :raises DuplicateException: If match interferences already exist for the given sample item and isotopes.
    """
    print("Saving match interferences to database")
    sample_item_id = match_interferences[0].sample_item_id
    target_isotope_ids = [mi.target_isotope_id for mi in match_interferences]
    async with async_session() as session:
        # Step 1: Check for existing match interferences to avoid duplication.
        stmt = select(MatchInterference).where(
            and_(
                MatchInterference.sample_item_id == sample_item_id,
                MatchInterference.target_isotope_id.in_(target_isotope_ids),
            )
        )
        existing_interferences = (await session.execute(stmt)).scalars().all()
        # If existing match interference are found, raise a DuplicateException to prevent overwriting.
        if existing_interferences:
            raise DuplicateException(
                "Match interferences already exist for the given sample item and target isotopes."
            )

        # Step 2: Insert the new match interference into the database and commit the transaction.
        new_match_interferences = [
            MatchInterference(**mi.dict()) for mi in match_interferences
        ]
        session.add_all(new_match_interferences)
        await session.commit()

        # Step 3: Refresh the match interferences to get updated data from the database.
        for interference in new_match_interferences:
            await session.refresh(interference)

    # Step 4: Return created match interferences
    message = (
        f"{len(new_match_interferences)} match interference(s) created successfully."
    )
    print(message)
    return {
        "message": message,
        "data": [interference.to_dict() for interference in new_match_interferences],
    }
