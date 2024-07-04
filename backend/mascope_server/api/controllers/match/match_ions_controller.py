from datetime import datetime, timezone
from typing import List, Optional
from collections import defaultdict
from sqlalchemy import select, delete, and_
from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.api.utils.api_features import api_controller
from mascope_server.api.controllers.match.util import fetch_sample_item_ids
from mascope_server.api.exceptions import (
    DuplicateException,
    ApiException,
)
from mascope_server.api.models.models import MatchIon
from mascope_server.api.models.pydantic_models.match_ion_pydantic_model import (
    MatchIonBase,
)


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
                        **match_ion.dict(),
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

    print(result["message"])
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

    print(message)
    return {"message": message}
