from datetime import datetime, timezone
from typing import List, Optional
from collections import defaultdict
from sqlalchemy import (
    select,
    delete,
    func,
)
from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.api.utils.api_features import api_controller
from mascope_server.api.exceptions import (
    DuplicateException,
    NotFoundException,
    ApiException,
)
from mascope_server.api.controllers.match.util import fetch_sample_item_ids
from mascope_server.api.models.models import MatchSample, SampleItem
from mascope_server.api.models.pydantic_models.match_sample_pydantic_model import (
    MatchSampleBase,
)

import mascope_runtime as runtime
logger = runtime.logger.service('backend')

@api_controller()
async def get_match_samples(
    sample_item_id: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    match_category: Optional[int] = None,
    sort: Optional[str] = None,
    order: Optional[str] = None,
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a list of match samples based on filter criteria, including sample item ID and batch ID.
    Results can be sorted and paginated according to the provided parameters.

    Steps:
    1. Construct a query to fetch match samples.
    2. Apply filtering based on sample item ID, sample batch ID, and match category if specified.
    3. Apply sorting if specified.
    4. Count the total matching samples for pagination.
    5. Apply pagination and execute the query.
    6. Format the fetched match samples into a list of dictionaries for response.

    :param sample_item_id: Filter match samples by sample item ID, defaults to None.
    :type sample_item_id: Optional[str], optional
    :param sample_batch_id: Filter match samples by sample batch ID, defaults to None.
    :type sample_batch_id: Optional[str], optional
    :param match_category: Filter by the category of the match, defaults to None.
    :type match_category: Optional[int], optional
    :param sort: Column to sort the results by, defaults to None.
    :type sort: Optional[str], optional
    :param order: Sort order, either 'asc' or 'desc', defaults to None.
    :type order: Optional[str], optional
    :param page: Page number for pagination, defaults to 0.
    :type page: int, optional
    :param limit: Number of items per page, defaults to 10000.
    :type limit: int, optional
    :return: A dictionary containing the total count and a list of match samples.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct base query
        query = select(MatchSample)

        # Step 2: Apply filters
        if sample_item_id:
            query = query.filter(MatchSample.sample_item_id == sample_item_id)
        if match_category is not None:
            query = query.filter(MatchSample.match_category == match_category)
        if sample_batch_id:
            query = query.join(
                SampleItem, SampleItem.sample_item_id == MatchSample.sample_item_id
            ).filter(SampleItem.sample_batch_id == sample_batch_id)

        # Step 3: Apply sorting
        if sort:
            sort_expression = getattr(MatchSample, sort, None)
            if sort_expression:
                if order == "desc":
                    query = query.order_by(sort_expression.desc())
                else:
                    query = query.order_by(sort_expression.asc())

        # Step 4: Count total matching samples
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            query.subquery()
        )
        total = await session.scalar(count_stmt)

        # Step 5: Apply pagination
        query = query.offset(page * limit).limit(limit)

        # Step 6: Execute the query
        result = await session.execute(query)
    data = [item.to_dict() for item in result.scalars().all()]

    return {"results": total, "data": data}


@api_controller()
async def get_match_sample(match_sample_id: str) -> dict:
    """
    Retrieves information for a specific match sample by its unique identifier.

    Steps:
    1. Fetch the match sample using the provided ID to ensure it exists.
    2. Check if the match sample is found; if not, raise a NotFoundException.
    3. Return the match sample's details as a dictionary.

    :param match_sample_id: Unique identifier of the match sample to retrieve.
    :type match_sample_id: str
    :raises NotFoundException: If the match sample with the given ID is not found.
    :return: The detailed information of the match sample.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch match sample by ID
        sample = await session.get(MatchSample, match_sample_id)

    # Step 2: Check if the sample is found
    if not sample:
        raise NotFoundException(f"Match sample with ID '{match_sample_id}' not found")

    # Step 3: Return sample details
    return sample.to_dict()


@api_controller()
async def create_match_samples(
    match_samples: List[MatchSampleBase],
    independent_transaction: bool = False,
):
    """
    Creates match samples for a given sample item based on the provided list of aggregated match sample data.

    Steps:
    1. Group match samples by sample item ID.
    2. For each group, check for existing match samples to avoid duplication.
    3. Insert new match samples into the database.
    4. Commit the transaction and refresh the newly created match samples.
    5. Handle and report any duplication errors, raising an exception if no samples were successfully created.

    :param match_samples: List of match sample data for creating matches.
    :type match_samples: List[MatchSampleBase]
    :param independent_transaction: Indicates if the operation should be independent of any ongoing transactions, defaults to False.
    :type independent_transaction: bool, optional
    :return: The created match samples data.
    :rtype: dict
    :raises ApiException: If no match samples could be created due to DuplicateException errors.
    """
    # Step 1: Group match samples by sample item ID.
    grouped_match_samples = defaultdict(list)
    for match_sample in match_samples:
        grouped_match_samples[match_sample.sample_item_id].append(match_sample)

    new_match_samples = []
    errors = []
    async with async_session() as session:
        for sample_item_id, match_samples in grouped_match_samples.items():
            try:
                # Step 2: Check for existing match samples to avoid duplication.
                stmt = select(MatchSample).where(
                    MatchSample.sample_item_id == sample_item_id,
                )
                existing_match_samples = (await session.execute(stmt)).scalars().all()
                if existing_match_samples:
                    raise DuplicateException(
                        f"Match samples already exist for the given sample item '{sample_item_id}'."
                    )

                # Step 3: Insert new match samples
                for match_sample in match_samples:
                    new_match_sample = MatchSample(
                        match_sample_id=gen_id(32),
                        **match_sample.dict(),
                        match_sample_utc_created=datetime.now(timezone.utc),
                    )
                    session.add(new_match_sample)
                    new_match_samples.append(new_match_sample)
            except DuplicateException as e:
                errors.append({"sample_item_id": sample_item_id, "error": str(e)})

        # Step 4: Commit the transaction and refresh the newly created match samples.
        await session.commit()
        for match_sample in new_match_samples:
            await session.refresh(match_sample)

    # Step 5: Handle and report any duplication errors, raising an exception if no samples were successfully created.
    result = {}
    message = ""
    if new_match_samples:
        message = f"{len(new_match_samples)} match sample{'s' if len(new_match_samples) != 1 else ''} created successfully. "
        result["message"] = message
        result["data"] = [sample.to_dict() for sample in new_match_samples]
    if errors:
        message = (
            message
            + f"Failed to create match samples for {len(errors)} sample{'s' if len(errors) != 1 else ''}."
        )
        result["message"] = message
        result["errors"] = errors

    if errors and not new_match_samples:
        user_message = f"Failed to create match samples for {len(errors)} sample{'s' if len(errors) != 1 else ''}."

        raise ApiException(
            user_message,
            {
                "errors": errors,
            },
            409,
        )
    logger.info(message)
    return result


@api_controller()
async def delete_match_samples(
    sample_item_id: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
):
    """
    Deletes match samples for specified sample items.

    Steps:
    1. Fetch sample item IDs using the utility function.
    2. Construct and execute a delete query for match samples based on the sample item IDs.
    3. Commit the transaction and report the number of deleted records.

    :param sample_item_id: ID of the single sample item, optional.
    :param sample_batch_id: ID of the sample batch, optional.
    :return: A message indicating the outcome of the deletion process.
    """
    sample_item_ids, sample_ref = await fetch_sample_item_ids(
        sample_item_id, sample_batch_id
    )
    async with async_session() as session:
        query = delete(MatchSample).where(
            MatchSample.sample_item_id.in_(sample_item_ids)
        )
        result = await session.execute(query)
        await session.commit()
        deleted_count = result.rowcount

    message = f"{deleted_count} match sample{'s' if deleted_count != 1 else ''} deleted for {sample_ref}."
    logger.info(message)
    return {"message": message}
