from datetime import datetime, timezone
from typing import List, Optional
from collections import defaultdict
from sqlalchemy import (
    select,
    and_,
    delete,
    func,
)
from mascope_backend.db import async_session
from mascope_backend.db.id import gen_id
from mascope_backend.db.models import MatchCollection, SampleItem
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.lib.exceptions.api_exceptions import (
    DuplicateException,
    NotFoundException,
    ApiException,
)
from mascope_backend.api.controllers.sample.lib.sample_items_fetch import (
    fetch_sample_item_ids,
)
from mascope_backend.api.models.match.collections.match_collection_pydantic_model import (
    MatchCollectionBase,
)


from mascope_backend.runtime import runtime


@api_controller()
async def get_match_collections(
    sample_item_id: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    target_collection_id: Optional[str] = None,
    match_category_min: Optional[int] = None,
    sort: Optional[str] = None,
    order: Optional[str] = None,
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a list of matched collections based on filter criteria.
    Results can be sorted and paginated according to the provided parameters.

    Steps:
    1. Construct the base query to select from MatchCollection.
    2. Apply filters based on provided criteria such as sample item ID, batch ID, target collection ID, and match category.
    3. Apply sorting if specified.
    4. Count the total matched collections for pagination.
    5. Apply pagination and execute the query to fetch results.
    6. Convert the fetched match collections into a list of dictionaries for response.

    :param sample_item_id: Filter match collections by the ID of the sample item, defaults to None.
    :type sample_item_id: Optional[str], optional
    :param sample_batch_id: Filter match collections by the ID of the sample batch, defaults to None.
    :type sample_batch_id: Optional[str], optional
    :param target_collection_id: Filter match collections by the ID of the target collection, defaults to None.
    :type target_collection_id: Optional[str], optional
    :param match_category_min: Filter by match_category to include specified category and higher (e.g., 1 includes categories 1 and higher), defaults to None.
    :type match_category_min:int, optional
    :param sort: Column to sort the results by, defaults to None.
    :type sort: Optional[str], optional
    :param order: Sort order, either 'asc' for ascending or 'desc' for descending, defaults to None.
    :type order: Optional[str], optional
    :param page: Page number for pagination, defaults to 0.
    :type page: int, optional
    :param limit: Number of items per page, defaults to 10000.
    :type limit: int, optional
    :return: A dictionary containing the total count and a list of matched collections.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct base query
        query = select(MatchCollection)

        # Step 2: Apply filters
        if sample_item_id:
            query = query.filter(MatchCollection.sample_item_id == sample_item_id)
        if target_collection_id:
            query = query.filter(
                MatchCollection.target_collection_id == target_collection_id
            )
        if match_category_min is not None:
            query = query.filter(MatchCollection.match_category == match_category_min)
        if sample_batch_id:
            query = query.join(
                SampleItem, SampleItem.sample_item_id == MatchCollection.sample_item_id
            ).filter(SampleItem.sample_batch_id == sample_batch_id)

        # Step 3: Apply sorting
        if sort:
            sort_expression = getattr(MatchCollection, sort, None)
            if sort_expression:
                if order == "desc":
                    query = query.order_by(sort_expression.desc())
                else:
                    query = query.order_by(sort_expression.asc())

        # Step 4: Count total matching collections
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            query.subquery()
        )
        total = await session.scalar(count_stmt)

        # Step 5: Apply pagination
        query = query.offset(page * limit).limit(limit)
        # Step 6: Execute the query and fetch results
        result = await session.execute(query)
    data = [item.to_dict() for item in result.scalars().all()]

    return {
        "message": "Match collections retrieved successfully",
        "results": total,
        "data": data,
    }


@api_controller()
async def get_match_collection(match_collection_id: str) -> dict:
    """
    Retrieves information for a specific match collection by its ID.

    Steps:
    1. Fetch the match collection using the provided ID to ensure it exists.
    2. Check if the match collection is found; if not, raise a NotFoundException.
    3. Return the match collection's details as a dictionary.

    :param match_collection_id: Unique identifier of the match collection to retrieve.
    :type match_collection_id: str
    :raises NotFoundException: If the match collection with the given ID is not found.
    :return: The detailed information of the match collection.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch match collection by ID
        collection = await session.get(MatchCollection, match_collection_id)

    # Step 2: Check if the collection is found
    if not collection:
        raise NotFoundException(
            f"Match collection with ID '{match_collection_id}' not found"
        )

    # Step 3: Return collection details
    return {
        "message": "Match collection retrieved successfully",
        "data": collection.to_dict(),
    }


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
                        **match_collection.model_dump(),
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

    runtime.logger.info(message)
    return result


@api_controller()
async def delete_match_collections(
    sample_item_id: str | None = None,
    sample_batch_id: str | None = None,
    target_collections_ids: list[str] | None = None,
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

    runtime.logger.info(message)
    return {"message": message}
