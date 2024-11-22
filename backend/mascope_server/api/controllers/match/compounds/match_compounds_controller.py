from datetime import datetime, timezone
from typing import List, Optional
import pandas as pd
from collections import defaultdict
from sqlalchemy import (
    select,
    delete,
    func,
    and_,
)

from mascope_lib.file_func import get_instrument_type

from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.db.models import (
    MatchCompound,
    Sample,
    TargetCompound,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
    TargetCollection,
)
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.lib.exceptions.api_exceptions import (
    DuplicateException,
    NotFoundException,
    ApiException,
)
from mascope_server.api.controllers.match.lib.match_util import deduplicate_match_df
from mascope_server.api.controllers.sample.lib.sample_items_fetch import (
    fetch_sample_item_ids,
)
from mascope_server.api.models.match.compounds.match_compound_pydantic_model import (
    MatchCompoundBase,
)


from mascope_server.runtime import runtime


@api_controller()
async def get_match_compounds(
    sample_item_id: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    target_compound_id: Optional[str] = None,
    match_category_min: Optional[int] = None,
    deduplicate: bool = False,
    show_target_collection: bool = False,
    show_target_compound: bool = False,
    sort: Optional[str] = None,
    order: Optional[str] = None,
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a list of matched compounds based on filtering criteria. This function allows
    for querying with options to include additional related data such as target compounds and collections.

    Steps:
    1. Construct the base query for fetching match compounds from the database.
    2. Apply filters based on provided sample item ID, sample batch ID, target compound ID, and match category.
    3. Optionally join with the TargetCompound and TargetCollection tables if related data is requested.
    4. Apply sorting if a sort column and order are specified.
    5. Count the total entries that match the criteria for pagination purposes.
    6. Limit the query for pagination and fetch the results.
    7. Format the fetched data into a dictionary for the response.
    8. If deduplication is requested and `show_target_collection` is True, deduplicate the compounds.

    :param sample_item_id: Filter matches by the associated sample item's ID, defaults to None.
    :type sample_item_id: Optional[str], optional
    :param sample_batch_id: Filter matches by the associated sample batch's ID, defaults to None.
    :type sample_batch_id: Optional[str], optional
    :param target_compound_id: Filter matches by the associated target compound's ID, defaults to None.
    :type target_compound_id: Optional[str], optional
    :param match_category_min: Filter by match_category to include specified category and higher (e.g., 1 includes categories 1 and higher), defaults to None.
    :type match_category_min:int, optional
    :param deduplicate: Flag to indicate whether compound deduplication should be applied when show_target_collection is True, defaults to False.
    :type deduplicate: bool
    :param show_target_collection: Include additional data about the target collections, defaults to False.
    :type show_target_collection: bool, optional
    :param show_target_compound: Include additional data about the target compounds, defaults to False.
    :type show_target_compound: bool, optional
    :param sort: Column name to sort by, defaults to None.
    :type sort: Optional[str], optional
    :param order: Order of sorting, 'asc' for ascending or 'desc' for descending, defaults to None.
    :type order: Optional[str], optional
    :param page: Page number for pagination, starts from 0, defaults to 0.
    :type page: int, optional
    :param limit: Maximum number of results per page, defaults to 10000.
    :type limit: int, optional
    :return: A dictionary containing total results count and the paginated list of match compounds.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Define the main query for match compounds
        query = select(MatchCompound)

        # Step 2: Apply basic fields filters if provided
        if sample_item_id:
            query = (
                query.filter(MatchCompound.sample_item_id == sample_item_id)
                .join(Sample, Sample.sample_item_id == sample_item_id)
                .add_columns(Sample.filename)
            )
        if target_compound_id:
            query = query.filter(MatchCompound.target_compound_id == target_compound_id)
        if match_category_min is not None:
            query = query.filter(MatchCompound.match_category >= match_category_min)

        # Join with TargetCompound table to include target_compound data if requested
        if show_target_compound:
            query = query.join(
                TargetCompound,
                TargetCompound.target_compound_id == MatchCompound.target_compound_id,
            ).add_columns(
                TargetCompound.target_compound_name,
                TargetCompound.target_compound_formula,
            )

        if sample_batch_id:
            query = (
                query.join(
                    Sample, Sample.sample_item_id == MatchCompound.sample_item_id
                )
                .where(Sample.sample_batch_id == sample_batch_id)
                .add_columns(Sample.filename)
            )

        # Join with TargetCompoundInTargetCollection to include target_collection data
        if show_target_collection:
            query = (
                query.join(
                    TargetCompoundInTargetCollection,
                    TargetCompoundInTargetCollection.target_compound_id
                    == MatchCompound.target_compound_id,
                )
                .join(
                    TargetCollectionInSampleBatch,
                    TargetCollectionInSampleBatch.target_collection_id
                    == TargetCompoundInTargetCollection.target_collection_id,
                )
                .where(
                    Sample.sample_batch_id
                    == TargetCollectionInSampleBatch.sample_batch_id
                )
                .join(
                    TargetCollection,
                    TargetCollection.target_collection_id
                    == TargetCompoundInTargetCollection.target_collection_id,
                )
                .add_columns(
                    TargetCompoundInTargetCollection.target_collection_id,
                    TargetCollection.target_collection_name,
                    TargetCollection.target_collection_type,
                )
                .distinct()
            )
        # Step 4: Apply sorting
        if sort:
            sort_expression = getattr(MatchCompound, sort, None)
            if sort_expression:
                if order == "desc":
                    query = query.order_by(sort_expression.desc())
                else:
                    query = query.order_by(sort_expression.asc())

        # Step 5: Count total
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            query.subquery()
        )
        total = await session.scalar(count_stmt)

        # Step 6: Execute the paginated query
        query = query.offset(page * limit).limit(limit)
        result = await session.execute(query)

    # Step 7: Construct response data
    data = []
    for row in result.all():
        match_compound_data = row.MatchCompound.to_dict()

        # Resolve correct intensity units based on the instrument type of the sample
        instrument_type = get_instrument_type(row.filename)
        if instrument_type == "tof":
            unit = "ions"
        else:
            unit = "rel."
        match_compound_data["unit"] = unit

        if show_target_compound:
            match_compound_data["target_compound_name"] = row.target_compound_name
            match_compound_data["target_compound_formula"] = row.target_compound_formula
        if show_target_collection:
            match_compound_data["target_collection_id"] = row.target_collection_id
            match_compound_data["target_collection_name"] = row.target_collection_name
            match_compound_data["target_collection_type"] = row.target_collection_type
        data.append(match_compound_data)

    # Step 8: Deduplicate if requested and `show_target_collection` is True
    if deduplicate and show_target_collection:
        data_df = pd.DataFrame(data)
        data_df = deduplicate_match_df(
            data_df, id_keys=("target_compound_id", "sample_item_id")
        )
        data = data_df.to_dict(orient="records")
        # Update total after deduplication
        total = len(data)
    return {"results": total, "data": data}


@api_controller()
async def get_match_compound(match_compound_id: str) -> dict:
    """
    Retrieves information for a specific match compound identified by its ID.

    Steps:
    1. Fetch the match compound from the database using its ID to ensure it exists.
    2. If not found, raise a NotFoundException.
    3. Return the details of the match compound as a dictionary.

    :param match_compound_id: Unique identifier of the match compound to retrieve.
    :type match_compound_id: str
    :raises NotFoundException: If no match compound is found with the specified ID.
    :return: Detailed information of the match compound.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch match compound by ID
        compound = await session.get(MatchCompound, match_compound_id)

    # Step 2: Check if the compound exists
    if not compound:
        raise NotFoundException(
            f"Match compound with ID '{match_compound_id}' not found"
        )

    # Step 3: Return compound details
    return compound.to_dict()


@api_controller()
async def create_match_compounds(
    match_compounds: List[MatchCompoundBase],
    independent_transaction: bool = False,
):
    """
    Creates match compounds for a given sample item based on the provided list of aggregated match compound data.

    Steps:
    1. Group match compounds by sample item ID.
    2. For each group, check for existing match compounds to avoid duplication.
    3. Insert new match compounds into the database.
    4. Commit the transaction and refresh the newly created match compounds.
    5. Handle and report any duplication errors, raising an exception if no compounds were successfully created.

    :param match_compounds: List of match compound data for creating matches.
    :type match_compounds: List[MatchCompoundBase]
    :param independent_transaction: Indicates if the operation should be independent of any ongoing transactions, defaults to False.
    :type independent_transaction: bool, optional
    :return: The created match compounds data.
    :rtype: dict
    :raises ApiException: If no match compounds could be created due to DuplicateException errors.
    """
    # Step 1: Group match compounds by sample item ID.
    grouped_match_compounds = defaultdict(list)
    for match_compound in match_compounds:
        grouped_match_compounds[match_compound.sample_item_id].append(match_compound)

    new_match_compounds = []
    errors = []
    async with async_session() as session:
        for sample_item_id, match_compounds in grouped_match_compounds.items():
            try:
                # Step 2: Check for existing match compounds to avoid duplication.
                target_compound_ids = [
                    match_compound.target_compound_id
                    for match_compound in match_compounds
                ]

                stmt = select(MatchCompound).where(
                    and_(
                        MatchCompound.sample_item_id == sample_item_id,
                        MatchCompound.target_compound_id.in_(target_compound_ids),
                    )
                )
                existing_match_compounds = (await session.execute(stmt)).scalars().all()
                if existing_match_compounds:
                    raise DuplicateException(
                        f"Match compounds already exist for the given sample item '{sample_item_id}' and target compounds."
                    )

                # Step 3: Insert new match compounds
                for match_compound in match_compounds:
                    new_match_compound = MatchCompound(
                        match_compound_id=gen_id(32),
                        **match_compound.model_dump(),
                        match_compound_utc_created=datetime.now(timezone.utc),
                    )
                    session.add(new_match_compound)
                    new_match_compounds.append(new_match_compound)
            except DuplicateException as e:
                errors.append({"sample_item_id": sample_item_id, "error": str(e)})

        # Step 4: Commit the transaction and refresh the newly created match compounds.
        await session.commit()
        for match_compound in new_match_compounds:
            await session.refresh(match_compound)

    # Step 5: Handle and report any duplication errors, raising an exception if no compounds were successfully created.
    result = {}
    message = ""
    if new_match_compounds:
        message = f"{len(new_match_compounds)} match compound{'s' if len(new_match_compounds) != 1 else ''} created successfully. "
        result["message"] = message
        result["data"] = [compound.to_dict() for compound in new_match_compounds]
    if errors:
        message = (
            message
            + f"Failed to create match compounds for {len(errors)} sample{'s' if len(errors) != 1 else ''}."
        )
        result["message"] = message
        result["errors"] = errors

    if errors and not new_match_compounds:
        user_message = f"Failed to create match compounds for {len(errors)} sample{'s' if len(errors) != 1 else ''}."

        raise ApiException(
            user_message,
            {
                "errors": errors,
            },
            409,
        )

    runtime.logger.info(message)
    return result


@api_controller()
async def delete_match_compounds(
    sample_item_id: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    target_compound_ids: Optional[List[str]] = None,
):
    """
    Deletes match compounds for specified sample items, optionally filtered by target compound IDs.
    This operation can be performed on a single sample item or a batch of items and can be restricted to specific compounds if target compound IDs are provided.

    Steps:
    1. Fetch sample item IDs using the utility function.
    2. Construct and execute a delete query for match compounds based on the sample item IDs.
       Apply an additional filter to restrict the deletion to specific target compounds if these IDs are provided.
    3. Commit the transaction and report the number of deleted records.

    :param sample_item_id: ID of the single sample item, optional.
    :param sample_batch_id: ID of the sample batch, optional.
    :param target_compound_ids: Optional list of target compound IDs.
    :return: A message indicating the outcome of the deletion process.
    """
    sample_item_ids, sample_ref = await fetch_sample_item_ids(
        sample_item_id, sample_batch_id
    )
    async with async_session() as session:
        query = delete(MatchCompound).where(
            MatchCompound.sample_item_id.in_(sample_item_ids)
        )
        if target_compound_ids:
            query = query.where(
                MatchCompound.target_compound_id.in_(target_compound_ids)
            )
        result = await session.execute(query)
        await session.commit()
        deleted_count = result.rowcount

    message = f"{deleted_count} match compound{'s' if deleted_count != 1 else ''} deleted for {sample_ref}."
    if target_compound_ids:
        message += f" Limited by {len(target_compound_ids)} specified target compound{'s' if len(target_compound_ids) != 1 else ''}."

    runtime.logger.info(message)
    return {"message": message}
