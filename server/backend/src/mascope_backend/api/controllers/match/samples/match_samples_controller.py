from datetime import datetime, timezone
from collections import defaultdict
from sqlalchemy import (
    select,
    delete,
    func,
)
from mascope_backend.db import async_session
from mascope_backend.db.id import gen_id
from mascope_backend.db.models import MatchSample, SampleItem
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.lib.exceptions.api_exceptions import (
    NotFoundException,
)
from mascope_backend.api.controllers.sample.lib.sample_items_fetch import (
    fetch_sample_item_ids,
)
from mascope_backend.api.models.match.samples.match_sample_pydantic_model import (
    MatchSampleBase,
)


from mascope_backend.runtime import runtime


@api_controller()
async def get_match_samples(
    sample_item_id: str | None = None,
    sample_batch_id: str | None = None,
    match_category_min: int | None = None,
    sort: str | None = None,
    order: str | None = None,
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
    :type sample_item_id: str | None, optional
    :param sample_batch_id: Filter match samples by sample batch ID, defaults to None.
    :type sample_batch_id: str | None, optional
    :param match_category_min: Filter by match_category to include specified category and higher (e.g., 1 includes categories 1 and higher), defaults to None.
    :type match_category_min: int | None, optional
    :param sort: Column to sort the results by, defaults to None.
    :type sort: str | None, optional
    :param order: Sort order, either 'asc' or 'desc', defaults to None.
    :type order: str | None, optional
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
        if match_category_min is not None:
            query = query.filter(MatchSample.match_category == match_category_min)
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

    return {
        "message": "Match samples retrieved successfully",
        "results": total,
        "data": data,
    }


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
    return {"message": "Match sample retrieved successfully", "data": sample.to_dict()}


@api_controller()
async def create_match_samples(
    match_samples: list[MatchSampleBase],
    independent_transaction: bool = False,
) -> dict:
    """
    Creates or updates match samples for a given sample based on the provided list of
    aggregated match sample data.
    Updates existing records if data differs, skips if identical, creates if new.

    :param match_samples: List of match sample data for creating matches
    :type match_samples: List[MatchSampleBase]
    :param independent_transaction: Indicates if operation should be independent
    :type independent_transaction: bool
    :return: Creation results with counts of new vs existing records
    :rtype: dict
    """
    if not match_samples:
        return {"message": "No match samples provided", "data": []}

    # Step 1: Group match samples by sample item ID.
    grouped_match_samples = defaultdict(list)
    for match_sample in match_samples:
        grouped_match_samples[match_sample.sample_item_id].append(match_sample)

    new_match_samples = []
    updated_count = 0
    unchanged_count = 0

    async with async_session() as session:
        for sample_item_id, m_samples in grouped_match_samples.items():
            provided_match_sample = m_samples[0]
            # Step 2: Check for existing match sample
            existing_sample = (
                (
                    await session.execute(
                        select(MatchSample).where(
                            MatchSample.sample_item_id == sample_item_id
                        )
                    )
                )
                .scalars()
                .one_or_none()
            )

            if existing_sample:
                # Step 3: Compare data and update if different
                needs_update = (
                    existing_sample.match_score != provided_match_sample.match_score
                    or existing_sample.match_category
                    != provided_match_sample.match_category
                    or existing_sample.sample_peak_intensity_sum
                    != provided_match_sample.sample_peak_intensity_sum
                )
                if needs_update:
                    existing_sample.match_score = provided_match_sample.match_score
                    existing_sample.match_category = (
                        provided_match_sample.match_category
                    )
                    existing_sample.sample_peak_intensity_sum = (
                        provided_match_sample.sample_peak_intensity_sum
                    )
                    existing_sample.match_sample_utc_modified = datetime.now(
                        timezone.utc
                    )
                    updated_count += 1
                    new_match_samples.append(existing_sample)
                    runtime.logger.trace(
                        f"Updated match sample for sample '{sample_item_id}'"
                    )
                else:
                    unchanged_count += 1
                    runtime.logger.trace(
                        f"Match sample unchanged for sample '{sample_item_id}'"
                    )
            else:
                # Step 4: Create new match sample
                new_match_sample = MatchSample(
                    match_sample_id=gen_id(32),
                    **provided_match_sample.model_dump(),
                    match_sample_utc_created=datetime.now(timezone.utc),
                )
                session.add(new_match_sample)
                new_match_samples.append(new_match_sample)

        # Step 5: Commit the transaction and refresh the newly created match samples.
        if new_match_samples:
            await session.commit()
            for sample in new_match_samples:
                await session.refresh(sample)

    # Step 6: Generate result message
    total_requested = len(match_samples)
    created_count = len(new_match_samples) - updated_count

    if created_count > 0 and (updated_count > 0 or unchanged_count > 0):
        status = "partial"
        message = f"Processed {total_requested} match samples: {created_count} created, {updated_count} updated, {unchanged_count} unchanged"
    elif created_count > 0 or updated_count > 0:
        status = "success"
        action = "created" if created_count > 0 else "updated"
        count = created_count if created_count > 0 else updated_count
        message = f"{action.title()} {count}/{total_requested} match sample{'s' if count != 1 else ''}"
    else:
        status = "skipped"
        message = f"All {unchanged_count} match samples unchanged"

    runtime.logger.info(message)

    return {
        "status": status,
        "message": message,
        "data": [match_sample.to_dict() for match_sample in new_match_samples],
    }


@api_controller()
async def delete_match_samples(
    sample_item_id: str | None = None,
    sample_batch_id: str | None = None,
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
    runtime.logger.info(message)
    return {"message": message}
