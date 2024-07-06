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
from mascope_server.api.models.models import MatchCompound
from mascope_server.api.models.pydantic_models.match_compound_pydantic_model import (
    MatchCompoundBase,
)


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
                        **match_compound.dict(),
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

    print(message)
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

    print(message)
    return {"message": message}
