from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import asc, desc, func, select, delete, and_
from mascope_server.db import async_session
from mascope_server.db.models import (
    MatchIsotope,
)
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.lib.exceptions.api_exceptions import (
    NotFoundException,
    DuplicateException,
)
from mascope_server.api.controllers.sample.lib.sample_items_fetch import (
    fetch_sample_item_ids,
)
from mascope_server.api.models.match.isotopes.match_isotopes_pydantic_model import (
    MatchIsotopeBase,
)


from mascope_server.runtime import runtime


@api_controller()
async def get_match_isotopes(
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
        stmt = select(MatchIsotope)

        # Step 2: Apply filters if specified
        if sample_item_id:
            stmt = stmt.filter(MatchIsotope.sample_item_id == sample_item_id)
        if target_isotope_id:
            stmt = stmt.filter(MatchIsotope.target_isotope_id == target_isotope_id)

        # Step 3: Apply sorting
        if sort:
            sort_expression = (
                desc(getattr(MatchIsotope, sort))
                if order == "desc"
                else asc(getattr(MatchIsotope, sort))
            )
            stmt = stmt.order_by(sort_expression)

        # Step 4: Apply pagination
        total = await session.scalar(
            select(func.count()).select_from(stmt)  # pylint: disable=not-callable
        )
        stmt = stmt.offset(page * limit).limit(limit)

        # Step 5: Execute query
        result = await session.execute(stmt)
    matches = result.scalars().all()

    # Step 6: Return results
    return {"results": total, "data": [match.to_dict() for match in matches]}


@api_controller()
async def get_match_isotope(match_isotope_id: str) -> dict:
    """
    Retrieves a single match by its unique ID.

    Steps:
    1. Execute a query to fetch the match with the specified ID.
    2. Check if the match exists. If not, raise a NotFoundException.
    3. Return the match's details as a dictionary.

    :param match_isotope_id: Unique identifier of the match to retrieve.
    :type match_isotope_id: str
    :return: The requested match's details.
    :rtype: dict
    :raises NotFoundException: If the match with the given ID is not found.
    """
    async with async_session() as session:
        # Step 1: Fetch match by ID
        match = await session.get(MatchIsotope, match_isotope_id)

    # Step 2: Check existence
    if not match:
        raise NotFoundException(f"MatchIsotope with ID '{match_isotope_id}' not found")

    # Step 3: Return match details
    return match.to_dict()


@api_controller()
async def delete_match_isotopes(
    sample_item_id: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    target_isotope_ids: Optional[List[str]] = None,
) -> dict:
    """
    Deletes match isotopes for specified sample items, optionally filtered by target isotope IDs.
    This operation supports deletion by either a single sample item ID, a batch of sample items from a sample batch,
    or can be restricted to specific isotopes if target isotope IDs are provided.

    Steps:
    1. Validate the input to ensure that either a sample item ID or a sample batch ID is provided.
    2. If a sample batch ID is provided, fetch the associated sample item IDs.
    3. Construct and execute a delete query for match isotopes based on the resolved sample item IDs.
       Apply an additional filter to restrict the deletion to specific target isotopes if these IDs are provided.
    4. Commit the transaction and report the number of deleted records.

    :param sample_item_id: ID of the single sample item for which match isotopes are to be deleted, optional.
    :type sample_item_id:  Optional[str]
    :param sample_batch_id: ID of the sample batch from which sample items are derived for deletion, optional.
    :type sample_batch_id:  Optional[str]
    :param target_isotope_ids: Optional list of target isotope IDs to further filter the match isotopes to be deleted.
    :type target_isotope_ids: Optional[List[str]]
    :return: A message indicating the outcome of the deletion process including the count of deleted records.
    :rtype: dict
    """
    sample_item_ids, sample_ref = await fetch_sample_item_ids(
        sample_item_id, sample_batch_id
    )

    async with async_session() as session:
        query = delete(MatchIsotope).where(
            MatchIsotope.sample_item_id.in_(sample_item_ids)
        )
        if target_isotope_ids:
            query = query.where(MatchIsotope.target_isotope_id.in_(target_isotope_ids))
        result = await session.execute(query)
        await session.commit()
        deleted_count = result.rowcount

    message = f"{deleted_count} match isotope{'s' if deleted_count != 1 else ''} deleted for {sample_ref}."
    if target_isotope_ids:
        message += f" Limited by {len(target_isotope_ids)} specified target isotope{'s' if len(target_isotope_ids) != 1 else ''}."

    runtime.logger.info(message)
    return {"message": message}


@api_controller()
async def create_match_isotopes(
    match_isotopes: List[MatchIsotopeBase],
    independent_transaction: bool = False,
):
    """
    Creates match isotopes for a given sample item based on the provided list of match isotope data.

    Steps:
    1. Check for existing match isotopeses to avoid duplication.
    2. Insert the new matches into the database and commit the transaction.
    3. Refresh and return the created match isotopes.

    :param match_isotopes: List of match isotope data for creating matches.
    :type match_isotopes: List[MatchIsotopeBase]
    :param independent_transaction: Indicates if the operation should be independent of any ongoing transactions, defaults to False.
    :type independent_transaction: bool, optional
    :return: The created match isotopes data.
    :rtype: dict
    :raises DuplicateException: If match isotopes already exist for the given sample item and target isotopes.
    """
    runtime.logger.info("Saving match isotopes to database")
    sample_item_id = match_isotopes[0].sample_item_id
    target_isotope_ids = [mi.target_isotope_id for mi in match_isotopes]

    async with async_session() as session:
        # Step 1: Check for existing match interferences to avoid duplication.
        stmt = select(MatchIsotope).where(
            and_(
                MatchIsotope.sample_item_id == sample_item_id,
                MatchIsotope.target_isotope_id.in_(target_isotope_ids),
            )
        )
        existing_match_isotopes = (await session.execute(stmt)).scalars().all()
        # If existing match isotopes are found, raise a DuplicateException to prevent overwriting.
        if existing_match_isotopes:
            raise DuplicateException(
                "Match isotopes already exist for the given sample item and target isotopes"
            )

        # Step 2: Insert the new match isotope into the database and commit the transaction.
        new_match_isotopes = [
            MatchIsotope(
                **mi.model_dump(), match_isotope_utc_created=datetime.now(timezone.utc)
            )
            for mi in match_isotopes
        ]
        session.add_all(new_match_isotopes)
        await session.commit()

        # Step 3: Refresh the match isotopes to get updated data from the database.
        for match_isotope in new_match_isotopes:
            await session.refresh(match_isotope)

    # Step 4: Return created match isotopes
    message = f"{len(new_match_isotopes)} match isotope(s) created successfully."
    runtime.logger.info(message)
    return {
        "message": message,
        "data": [match_isotope.to_dict() for match_isotope in new_match_isotopes],
    }
