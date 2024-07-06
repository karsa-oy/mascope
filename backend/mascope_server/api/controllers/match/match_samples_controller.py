from datetime import datetime, timezone
from typing import List, Optional
from collections import defaultdict
from sqlalchemy import select, delete
from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.api.utils.api_features import api_controller
from mascope_server.api.controllers.match.util import fetch_sample_item_ids
from mascope_server.api.exceptions import (
    DuplicateException,
    ApiException,
)
from mascope_server.api.models.models import MatchSample
from mascope_server.api.models.pydantic_models.match_sample_pydantic_model import (
    MatchSampleBase,
)


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
    print(message)
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
    print(message)
    return {"message": message}
