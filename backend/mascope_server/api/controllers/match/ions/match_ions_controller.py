from datetime import datetime, timezone
from typing import List, Optional
from collections import defaultdict
import pandas as pd
from sqlalchemy import (
    select,
    delete,
    func,
    and_,
)
from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.db.models import (
    MatchIon,
    Sample,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
    TargetCollection,
    TargetCompound,
    TargetIon,
    IonizationMechanism,
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
from mascope_server.api.models.match.ions.match_ion_pydantic_model import (
    MatchIonBase,
)


from mascope_server.runtime import runtime


@api_controller()
async def get_match_ions(
    sample_item_id: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    target_ion_id: Optional[str] = None,
    ionization_mechanism_id: Optional[str] = None,
    match_category_min: Optional[int] = None,
    deduplicate: bool = False,
    show_target_collection: bool = False,
    show_target_compound: bool = False,
    show_target_ion: bool = False,
    show_ionization_mechanism: bool = False,
    sort: Optional[str] = None,
    order: Optional[str] = None,
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a list of matched ions based on specified filtering criteria, supporting optional inclusion
    of related data (e.g., target collections, compounds, ions, and ionization mechanisms). The function
    supports sorting and pagination.

    Steps:
    1. Construct the main query for fetching matched ions from the database.
    2. Apply filters based on the provided `sample_item_id`, `target_ion_id`, and `match_category_min`.
    3. Join the `Sample` table if `sample_batch_id` is provided to filter matches by sample batch.
    4. Join the `TargetIon` table if required based on `ionization_mechanism_id`, `show_target_ion`,
    `show_ionization_mechanism`, or `show_target_collection` flags.
    5. Apply the filter for `ionization_mechanism_id` if provided.
    6. Join the `TargetCompound` table and add target compound details if `show_target_compound` is True.
    7. Add target ion details if `show_target_ion` is True.
    8. Join the `IonizationMechanism` table and add ionization mechanism details if `show_ionization_mechanism` is True.
    9. Join with target collection tables if `show_target_collection` is True to include related collection data.
    10. Apply sorting based on the specified `sort` column and `order` direction.
    11. Count the total number of matched ions for pagination.
    12. Limit the query for pagination and execute it to fetch the results.
    13. Format the fetched data into a list of dictionaries for the response.
    14. If deduplication is requested and `show_target_collection` is True, deduplicate the ions.

    :param sample_item_id: Filter matches by the sample item ID, defaults to None.
    :type sample_item_id: Optional[str], optional
    :param sample_batch_id: Filter matches by the sample batch ID, defaults to None.
    :type sample_batch_id: Optional[str], optional
    :param target_ion_id: Filter matches by the target ion ID, defaults to None.
    :type target_ion_id: Optional[str], optional
    :param ionization_mechanism_id: Filter matches by the ionization mechanism ID, defaults to None.
    :type ionization_mechanism_id: Optional[str], optional
    :param match_category_min: Filter by match_category to include specified category and higher (e.g., 1 includes categories 1 and higher), defaults to None.
    :type match_category_min:int, optional
    :param deduplicate: Flag to indicate whether ion deduplication should be applied when `show_target_collection` is True, defaults to False.
    :type deduplicate: bool
    :param show_target_collection: Whether to include target collection details, defaults to False.
    :type show_target_collection: bool, optional
    :param show_target_compound: Include additional data about the target compounds, defaults to False.
    :type show_target_compound: bool, optional
    :param show_target_ion: Include additional data about the target ions, defaults to False.
    :type show_target_ion: bool, optional
    :param show_ionization_mechanism: Include ionization mechanism data in the results, defaults to False.
    :type show_ionization_mechanism: bool
    :param sort: Column name to sort by, defaults to None.
    :type sort: Optional[str], optional
    :param order: Order of sorting, 'asc' for ascending or 'desc' for descending, defaults to None.
    :type order: Optional[str], optional
    :param page: Page number for pagination, starts from 0, defaults to 0.
    :type page: int, optional
    :param limit: Maximum number of results per page, defaults to 10000.
    :type limit: int, optional
    :return: A dictionary containing the total results count and a paginated list of match ions.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Define the main query for match ions
        query = select(MatchIon)

        # Step 2: Apply filters based on input parameters
        if sample_item_id:
            query = query.filter(MatchIon.sample_item_id == sample_item_id)
        if target_ion_id:
            query = query.filter(MatchIon.target_ion_id == target_ion_id)
        if match_category_min is not None:
            query = query.filter(MatchIon.match_category >= match_category_min)

        # Step 3: Join with Sample table if sample_batch_id is specified
        if sample_batch_id:
            query = query.join(
                Sample, Sample.sample_item_id == MatchIon.sample_item_id
            ).where(Sample.sample_batch_id == sample_batch_id)

        # Step 4: Join TargetIon if requested
        if (
            ionization_mechanism_id
            or show_target_collection
            or show_target_compound
            or show_target_ion
            or show_ionization_mechanism
        ):
            query = query.join(
                TargetIon, TargetIon.target_ion_id == MatchIon.target_ion_id
            )

        # Step 5: Apply filter for ionization mechanism if provided
        if ionization_mechanism_id:
            query = query.filter(
                TargetIon.ionization_mechanism_id == ionization_mechanism_id
            )

        # Step 6: Add target compound columns if requested
        if show_target_compound:
            query = query.join(
                TargetCompound,
                TargetCompound.target_compound_id == TargetIon.target_compound_id,
            ).add_columns(
                TargetCompound.target_compound_name,
                TargetCompound.target_compound_formula,
            )

        # Step 7: Add target ion columns
        if show_target_ion:
            query = query.add_columns(
                TargetIon.target_compound_id,
                TargetIon.target_ion_formula,
                TargetIon.filter_params,
            )

        # Step 8: Join IonizationMechanism and add columns if requested
        if show_ionization_mechanism:
            query = query.join(
                IonizationMechanism,
                IonizationMechanism.ionization_mechanism_id
                == TargetIon.ionization_mechanism_id,
            )
            query = query.add_columns(
                IonizationMechanism.ionization_mechanism,
            )

        # Step 9: Join with TargetCollection and add columns if requested
        if show_target_collection:
            query = (
                query.join(
                    TargetCompoundInTargetCollection,
                    TargetCompoundInTargetCollection.target_compound_id
                    == TargetIon.target_compound_id,
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

        # Step 10: Apply sorting
        if sort:
            sort_expression = getattr(MatchIon, sort, None)
            if sort_expression:
                if order == "desc":
                    query = query.order_by(sort_expression.desc())
                else:
                    query = query.order_by(sort_expression.asc())

        # Step 11: Count total
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            query.subquery()
        )
        total = await session.scalar(count_stmt)

        # Step 12: Execute the paginated query
        query = query.offset(page * limit).limit(limit)
        result = await session.execute(query)

    # Step 13: Construct response data
    data = []
    for row in result.all():
        ion_data = row.MatchIon.to_dict()
        if show_target_collection:
            ion_data["target_collection_id"] = row.target_collection_id
            ion_data["target_collection_name"] = row.target_collection_name
            ion_data["target_collection_type"] = row.target_collection_type
        if show_target_compound:
            ion_data["target_compound_name"] = row.target_compound_name
            ion_data["target_compound_formula"] = row.target_compound_formula
        if show_target_ion:
            ion_data["target_compound_id"] = row.target_compound_id
            ion_data["target_ion_formula"] = row.target_ion_formula
            ion_data["filter_params"] = row.filter_params
        if show_ionization_mechanism:
            ion_data["ionization_mechanism"] = row.ionization_mechanism
        data.append(ion_data)

    # Step 14: Deduplicate if requested and `show_target_collection` is True
    if deduplicate and show_target_collection:
        data_df = pd.DataFrame(data)
        data_df = deduplicate_match_df(
            data_df, id_keys=("target_ion_id", "sample_item_id")
        )
        data = data_df.to_dict(orient="records")
        # Update total after deduplication
        total = len(data)

    return {"results": total, "data": data}


@api_controller()
async def get_match_ion(match_ion_id: str) -> dict:
    """
    Retrieves detailed information for a specific match ion by its unique ID.

    Steps:
    1. Fetch the match ion from the database using its ID to ensure it exists.
    2. If the match ion is not found, raise a NotFoundException.
    3. Return the details of the match ion as a dictionary.

    :param match_ion_id: Unique identifier of the match ion to retrieve.
    :type match_ion_id: str
    :raises NotFoundException: If no match ion is found with the specified ID.
    :return: Detailed information of the match ion.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch match ion by ID
        ion = await session.get(MatchIon, match_ion_id)

    # Step 2: Check if the ion exists
    if not ion:
        raise NotFoundException(f"Match ion with ID '{match_ion_id}' not found")

    # Step 3: Return ion details
    return ion.to_dict()


@api_controller()
async def create_match_ions(
    match_ions: List[MatchIonBase],
    independent_transaction: bool = False,
):
    """
    Creates match ions for a given sample item based on the provided list of aggregated match ion data.

    Steps:
    1. Group match ions by sample item ID.
    2. For each group, check for existing match ions to avoid duplication.
    3. Insert new match ions into the database.
    4. Commit the transaction and refresh the newly created match ions.
    5. Handle and report any duplication errors, raising an exception if no ions were successfully created.

    :param match_ions: List of match ion data for creating matches.
    :type match_ions: List[MatchIonBase]
    :param independent_transaction: Indicates if the operation should be independent of any ongoing transactions, defaults to False.
    :type independent_transaction: bool, optional
    :return: The created match ions data.
    :rtype: dict
    :raises ApiException: If no match ions could be created due to DuplicateException errors.
    """
    # Step 1: Group match ions by sample item ID.
    grouped_match_ions = defaultdict(list)
    for match_ion in match_ions:
        grouped_match_ions[match_ion.sample_item_id].append(match_ion)

    new_match_ions = []
    errors = defaultdict(list)
    async with async_session() as session:
        for sample_item_id, match_ions in grouped_match_ions.items():
            for match_ion in match_ions:
                try:
                    # Step 2: Check for existing match ion to avoid duplication.
                    stmt = select(MatchIon).where(
                        and_(
                            MatchIon.sample_item_id == sample_item_id,
                            MatchIon.target_ion_id == match_ion.target_ion_id,
                        )
                    )
                    existing_match_ion = (
                        (await session.execute(stmt)).scalars().one_or_none()
                    )
                    if existing_match_ion:
                        raise DuplicateException(
                            f"Match ion already exist for the given sample item '{sample_item_id}' and target ion {match_ion.target_ion_id}."
                        )
                    # Step 3: Insert new match ions
                    new_match_ion = MatchIon(
                        match_ion_id=gen_id(32),
                        **match_ion.model_dump(),
                        match_ion_utc_created=datetime.now(timezone.utc),
                    )
                    session.add(new_match_ion)
                    new_match_ions.append(new_match_ion)
                except DuplicateException as e:
                    errors[sample_item_id].append(
                        {"target_ion_id": match_ion.target_ion_id, "error": str(e)}
                    )
                    continue  # Continue with next ion even if current one fails

        # Step 4: Commit the transaction and refresh the newly created match ions.
        if new_match_ions:
            await session.commit()  # Commit all successfully added to session ions
            for match_ion in new_match_ions:
                await session.refresh(match_ion)

    # Step 5: Handle and report any duplication errors, raising an exception if no ions were successfully created.
    result = {"message": ""}
    if new_match_ions:
        result[
            "message"
        ] += f"{len(new_match_ions)} match ion{'s' if len(new_match_ions) != 1 else ''} created successfully."
        result["data"] = [ion.to_dict() for ion in new_match_ions]

    if errors:
        error_count = sum(len(lst) for lst in errors.values())
        result[
            "message"
        ] += f" Failed to create match ions for {error_count} sample{'s' if error_count != 1 else ''}."
        result["errors"] = dict(errors)

    runtime.logger.info(result["message"])
    if not new_match_ions and errors:
        raise ApiException(
            f"Failed to create match ions due to duplicate issues for {error_count} samples.",
            {"errors": dict(errors)},
            409,
        )

    return result


@api_controller()
async def delete_match_ions(
    sample_item_id: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    target_ion_ids: Optional[List[str]] = None,
) -> dict:
    """
    Deletes match ions for specified sample items, optionally filtered by target ion IDs.
    This operation supports deletion by either a single sample item ID, a batch of sample items from a sample batch,
    or can be restricted to specific ions if target ion IDs are provided.

    Steps:
    1. Validate the input to ensure that either a sample item ID or a sample batch ID is provided.
    2. If a sample batch ID is provided, fetch the associated sample item IDs.
    3. Construct and execute a delete query for match ions based on the resolved sample item IDs.
       Apply an additional filter to restrict the deletion to specific target ions if these IDs are provided.
    4. Commit the transaction and report the number of deleted records.

    :param sample_item_id: ID of the single sample item for which match ions are to be deleted, optional.
    :type sample_item_id: Optional[str]
    :param sample_batch_id: ID of the sample batch from which sample items are derived for deletion, optional.
    :type sample_batch_id: Optional[str]
    :param target_ion_ids: Optional list of target ion IDs to further filter the match ions to be deleted.
    :type target_ion_ids: Optional[List[str]]
    :return: A message indicating the outcome of the deletion process including the count of deleted records.
    :rtype: dict
    """
    sample_item_ids, sample_ref = await fetch_sample_item_ids(
        sample_item_id, sample_batch_id
    )

    async with async_session() as session:
        query = delete(MatchIon).where(MatchIon.sample_item_id.in_(sample_item_ids))
        if target_ion_ids:
            query = query.where(MatchIon.target_ion_id.in_(target_ion_ids))
        result = await session.execute(query)
        await session.commit()
        deleted_count = result.rowcount

    message = f"{deleted_count} match ion{'s' if deleted_count != 1 else ''} deleted for {sample_ref}."
    if target_ion_ids:
        message += f" Limited by {len(target_ion_ids)} specified target ion{'s' if len(target_ion_ids) != 1 else ''}."

    runtime.logger.info(message)
    return {"message": message}
