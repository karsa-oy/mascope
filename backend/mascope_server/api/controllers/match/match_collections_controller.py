from datetime import datetime, timezone
from typing import List, Optional
from collections import defaultdict
from sqlalchemy import select, and_, delete
from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.api.utils.api_features import api_controller
from mascope_server.api.controllers.match.util import fetch_sample_item_ids
from mascope_server.api.exceptions import DuplicateException, ApiException
from mascope_server.api.models.models import MatchCollection
from mascope_server.api.models.pydantic_models.match_collection_pydantic_model import (
    MatchCollectionBase,
)


@api_controller()
async def create_match_collections(
    match_collections: List[MatchCollectionBase],
    independent_transaction: bool = False,
):
    """
    Creates match collections for a given sample item based on the provided list of aggregated match collection data.

    Steps:
    1. Group match collections by sample item ID.
    2. For each group, check for existing match collections to avoid duplication.
    3. Insert new match collections into the database.
    4. Commit the transaction and refresh the newly created match collections.
    5. Handle and report any duplication errors, raising an exception if no collections were successfully created.

    :param match_collections: List of match collection data for creating matches.
    :type match_collections: List[MatchCollectionBase]
    :param independent_transaction: Indicates if the operation should be independent of any ongoing transactions, defaults to False.
    :type independent_transaction: bool, optional
    :return: The created match collections data.
    :rtype: dict
    :raises ApiException: If no match collections could be created due to DuplicateException errors.
    """
    # Step 1: Group match collections by sample item ID.
    grouped_match_collections = defaultdict(list)
    for match_collection in match_collections:
        grouped_match_collections[match_collection.sample_item_id].append(
            match_collection
        )

    new_match_collections = []
    errors = []
    async with async_session() as session:
        for sample_item_id, match_collections in grouped_match_collections.items():
            try:
                # Step 2: Check for existing match collections to avoid duplication.
                target_collection_ids = [
                    collection.target_collection_id for collection in match_collections
                ]

                stmt = select(MatchCollection).where(
                    and_(
                        MatchCollection.sample_item_id == sample_item_id,
                        MatchCollection.target_collection_id.in_(target_collection_ids),
                    )
                )
                existing_match_collections = (
                    (await session.execute(stmt)).scalars().all()
                )
                if existing_match_collections:
                    raise DuplicateException(
                        f"Match collections already exist for the given sample item '{sample_item_id}' and target collections."
                    )

                # Step 3: Insert new match collections
                for match_collection in match_collections:
                    new_match_collection = MatchCollection(
                        match_collection_id=gen_id(32),
                        **match_collection.dict(),
                        match_collection_utc_created=datetime.now(timezone.utc),
                    )
                    session.add(new_match_collection)
                    new_match_collections.append(new_match_collection)
            except DuplicateException as e:
                errors.append({"sample_item_id": sample_item_id, "error": str(e)})

        # Step 4: Commit the transaction and refresh the newly created match collections.
        await session.commit()
        for match_collection in new_match_collections:
            await session.refresh(match_collection)

    # Step 5: Handle and report any duplication errors, raising an exception if no collections were successfully created.
    result = {}
    message = ""
    if new_match_collections:
        message = f"{len(new_match_collections)} match collection{'s' if len(new_match_collections) != 1 else ''} created successfully. "
        result["message"] = message
        result["data"] = [collection.to_dict() for collection in new_match_collections]
    if errors:
        message += f"Failed to create match collections for {len(errors)} sample{'s' if len(errors) != 1 else ''}."
        result["message"] = message
        result["errors"] = errors

    if errors and not new_match_collections:
        user_message = f"Failed to create match collections for {len(errors)} sample{'s' if len(errors) != 1 else ''}."
        raise ApiException(user_message, {"errors": errors}, 409)

    print(message)
    return result


@api_controller()
async def delete_match_collections(
    sample_item_id: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    target_collections_ids: Optional[List[str]] = None,
):
    """
    Deletes match collections for specified sample items, optionally filtered by target collection IDs.

    Steps:
    1. Fetch sample item IDs using the utility function.
    2. Construct and execute a delete query for match collections based on the sample item IDs.
       Apply an additional filter to restrict the deletion to specific target collections if these IDs are provided.
    3. Commit the transaction and report the number of deleted records.

    :param sample_item_id: ID of the single sample item, optional.
    :param sample_batch_id: ID of the sample batch, optional.
    :param target_collections_ids: Optional list of target collection IDs.
    :return: A message indicating the outcome of the deletion process.
    """
    sample_item_ids, sample_ref = await fetch_sample_item_ids(
        sample_item_id, sample_batch_id
    )
    async with async_session() as session:
        query = delete(MatchCollection).where(
            MatchCollection.sample_item_id.in_(sample_item_ids)
        )
        if target_collections_ids:
            query = query.where(
                MatchCollection.target_collection_id.in_(target_collections_ids)
            )
        result = await session.execute(query)
        await session.commit()
        deleted_count = result.rowcount

    message = f"{deleted_count} match collection{'s' if deleted_count != 1 else ''} deleted for {sample_ref}."
    if target_collections_ids:
        message += f" Limited by specified {len(target_collections_ids)} target collection{'s' if len(target_collections_ids) != 1 else ''}."

    print(message)
    return {"message": message}
