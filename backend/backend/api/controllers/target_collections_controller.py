# -------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import joinedload
from typing import List, Optional, Dict

from backend.api_sio import sio
from backend.db.id import gen_id
from backend.db import async_session

from .target_compounds_controller import (
    get_target_compounds,
    delete_target_compound,
    create_target_compound,
)
from .match_controller import rematch_batches
from ..models.models import (
    TargetCollection,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
    TargetCompound,
)
from ..models.pydantic_models.target_collection_pydantic_model import (
    TargetCollectionCreateBody,
    TargetCollectionUpdateBody,
)
from ..models.pydantic_models.match_pydantic_model import (
    RematchBatchBody,
    RematchBatchesBody,
)
from ..exceptions import process_exception, ApiException, NotFoundException


# -------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------


async def get_batches_compounds(sample_batches: List[str]) -> Dict[str, List[str]]:
    """
    Retrieves the target compounds associated with a list of sample batch IDs. This function is intended to gather
    the current state of target compounds for each batch, either before or after updates to the target collection.

    :param sample_batches: List of sample batch IDs to fetch target compounds for.
    :type sample_batches: List[str]
    :return: A dictionary with sample batch IDs as keys and lists of target compound IDs as values.
    :rtype: Dict[str, List[str]]

    Usage:
    - This function is used in the `update_target_collection` process, both before and after applying updates to the target collection,
      to understand the changes in the association of target compounds with sample batches. It aids in determining the need for and scope of rematch operations.
    """
    batches_compounds_dict = {}

    for sample_batch_id in sample_batches:
        batch_compounds_result = await get_target_compounds(
            sample_batch_id=sample_batch_id
        )

        # Extract target compound IDs from the result and assign to the corresponding batch ID in the dictionary
        batches_compounds_dict[sample_batch_id] = [
            compound["target_compound_id"]
            for compound in batch_compounds_result["data"]
        ]

    return batches_compounds_dict


# -------------------------------------------------------------------
# Main Logic Functions
# -------------------------------------------------------------------


async def compare_batches_compounds(
    batches_compounds_before_update: Dict[str, List[str]],
    batches_compounds_after_update: Dict[str, List[str]],
) -> List[RematchBatchBody]:
    """
    Compares the target compounds associated with sample batches before and after updates to identify changes.
    This function is used for determining which compounds have been added or removed from each batch as a result of updates to the target collection assosiations.


    :param batches_compounds_before_update: The state of target compounds associated with sample batches before the updates.
    :type batches_compounds_before_update: Dict[str, List[str]]
    :param batches_compounds_after_update: The state of target compounds associated with sample batches after the updates.
    :type batches_compounds_after_update: Dict[str, List[str]]
    :return: A list of `RematchBatchBody` objects, each representing a sample batch that requires a rematch operation. Each object includes the batch ID and lists of added or removed target compound IDs.
    :rtype: List[RematchBatchBody]

    Usage:
    - In the `update_target_collection` function, after applying updates, this function is used to identify the exact changes in target compound associations for each sample batch.
      The resulting list of `RematchBatchBody` objects is used to construct `RematchBatchesBody` for the background rematch task, ensuring that the rematch operation only affects the necessary target compounds.

    """
    rematch_batches = []

    # Combine keys from both dictionaries to ensure all batches are considered
    all_batch_ids = set(batches_compounds_before_update.keys()) | set(
        batches_compounds_after_update.keys()
    )

    for batch_id in all_batch_ids:
        # Get compounds before and after update, defaulting to empty list if not present
        compounds_before = set(batches_compounds_before_update.get(batch_id, []))
        compounds_after = set(batches_compounds_after_update.get(batch_id, []))

        # Determine added and removed compounds
        added_compounds = compounds_after - compounds_before
        removed_compounds = compounds_before - compounds_after

        # Create RematchBatchBody only if there are changes
        if added_compounds or removed_compounds:
            rematch_batch = RematchBatchBody(
                sample_batch_id=batch_id,
                added_target_compound_ids=list(added_compounds),
                removed_target_compound_ids=list(removed_compounds),
            )
            rematch_batches.append(rematch_batch)

    return rematch_batches


# -------------------------------------------------------------------
# Controller or Route Handlers
# -------------------------------------------------------------------


async def get_target_collections(
    target_collection_type: str,
    target_collection_name: str,
    sort: str,
    order: str,
    page: int,
    limit: int,
):
    async with async_session() as session:
        stmt = select(TargetCollection)

        if target_collection_type:
            stmt = stmt.where(
                TargetCollection.target_collection_type == target_collection_type
            )
        if target_collection_name:
            stmt = stmt.where(
                TargetCollection.target_collection_name == target_collection_name
            )
        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetCollection, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetCollection, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        target_collections = result.scalars().all()

        return {
            "results": total,
            "data": [
                target_collection.to_dict() for target_collection in target_collections
            ],
        }


async def get_target_collection(target_collection_id: str):
    async with async_session() as session:
        stmt = (
            select(TargetCollection)
            .options(
                # Load target compounds associated with target collection
                joinedload(TargetCollection.target_compound).joinedload(
                    TargetCompoundInTargetCollection.target_compound
                ),
                # Load sample batches associated with target collection
                joinedload(TargetCollection.sample_batch).joinedload(
                    TargetCollectionInSampleBatch.sample_batch
                ),
            )
            .filter(TargetCollection.target_collection_id == target_collection_id)
        )
        result = await session.execute(stmt)
        target_collection = result.scalars().first()

        if not target_collection:
            raise HTTPException(
                status_code=404,
                detail=f"TargetCollection with ID {target_collection_id} not found",
            )

        target_collection_dict = target_collection.to_dict()

        # Add associated target compounds to the target collection dictionary
        target_compounds = [
            tc.target_compound.to_dict() for tc in target_collection.target_compound
        ]

        # Add associated sample batches to the target collection dictionary
        sample_batches = [
            {
                "workspace_id": sb.sample_batch.workspace_id,
                "sample_batch_id": sb.sample_batch.sample_batch_id,
                "sample_batch_name": sb.sample_batch.sample_batch_name,
            }
            for sb in target_collection.sample_batch
        ]

        target_collection_dict["target_compounds_count"] = len(target_compounds)
        target_collection_dict["sample_batches_count"] = len(sample_batches)
        target_collection_dict["target_compounds"] = target_compounds
        target_collection_dict["sample_batches"] = sample_batches

        return target_collection_dict


async def create_target_collection(
    target_collection_create_body: TargetCollectionCreateBody,
    background_tasks: BackgroundTasks,
    sid=None,
) -> dict:
    """
    Creates a new target collection with the specified name, description, and type, and optionally associates it
    with new or existing target compounds and sample batches.

    The function processes the creation of a new target collection, including the creation of new target compounds if specified,
    and the association of existing target compounds with the collection. Function verifies the existence of provided target compound IDs in the database.
    It associates the newly created collection with specified sample batches and performs necessary rematch operations for affected sample batches due to
    changes in target collection associations.

    The function  compounds and sample batches. It also handles rematch operations for affected sample batches and emits necessary reload events.

    Steps:
    1. Initialize control variables and unpack the creation payload.
    2. Create a new target collection object with provided details.
    3. Process and create new target compounds if provided and log the creation details.
    4. Verify the existence of provided target compound IDs and log any excluded compounds.
    5. Associate both newly created and verified existing target compounds with the new collection.
    6. Associate the new target collection with specified sample batches and prepare for rematch operations if necessary.
    7. Commit the new target collection and its associations to the database.
    8. Perform rematch operations for affected sample batches due to the creation of the new collection.
    9. Emit reload events for affected sample batches and a global target reload event to inform all clients about the changes.
    10. Return the newly created target collection with its associations and a log of significant events during the creation process.


    :param target_collection_create_body: The data for creating the new target collection.
    :type target_collection_create_body: TargetCollectionCreateBody
    :param background_tasks: FastAPI background tasks for asynchronous execution of operations like rematching.
    :type background_tasks: BackgroundTasks
    :param sid: Session ID, used for emitting notifications to specific client, defaults to None.
    :type sid: str, optional
    :raises RuntimeError: If there's an error in creating target compounds.
    :raises ValueError: If no compounds are added to the target collection.
    :raises NotFoundException: If the target collection or associated entities are not found after creation.
    :raises ApiException: For handling and encapsulating exceptions occurred during the creation process.
    :return: A dictionary containing the newly created target collection object with its associations and a log of messages related to the creation process.
    :rtype: dict
    """
    try:
        # Step 1. Initialize control variables and unpack the create payload, reference as new_
        message_logs = {}
        affected_batches_to_rematch = set()
        sample_batches_to_reload = set()

        # Unpack create fields
        new_target_collection_name = (
            target_collection_create_body.target_collection_name
        )
        target_compounds_to_create = (
            target_collection_create_body.target_compounds_create
        )
        target_compound_ids = target_collection_create_body.target_compound_ids
        sample_batch_ids = target_collection_create_body.sample_batch_ids

        # Step 2: Create the new  target collection object
        async with async_session() as session:
            new_target_collection = TargetCollection(
                target_collection_id=gen_id(16),
                target_collection_name=new_target_collection_name,
                target_collection_description=target_collection_create_body.target_collection_description,
                target_collection_type=target_collection_create_body.target_collection_type,
            )
            session.add(new_target_collection)

            # Step 3: Process and create new target compounds if provided
            created_target_compound_ids = []
            if target_compounds_to_create and len(target_compounds_to_create) > 0:
                try:
                    # Create the target compounds
                    target_compounds_result = await create_target_compound(
                        target_compounds_to_create, session
                    )
                    created_target_compound_ids.extend(
                        target_compounds_result["target_compound_ids"]
                    )
                    message_logs["created_compounds_info"] = target_compounds_result[
                        "message_logs"
                    ]
                except Exception as e:
                    raise RuntimeError(
                        f"Error creating target compound: {str(e)}"
                    ) from e

            # Step 4: Verify that provided target compound ids to associate with collection exists in the database
            verified_target_compound_ids = []
            if target_compound_ids:
                stmt = select(TargetCompound.target_compound_id).where(
                    TargetCompound.target_compound_id.in_(target_compound_ids)
                )
                result = await session.execute(stmt)
                existing_compounds = result.scalars().all()
                verified_target_compound_ids = [
                    target_compound_id for target_compound_id in existing_compounds
                ]

                # Log excluded compounds if any
                excluded_compounds_count = len(
                    set(target_compound_ids) - set(verified_target_compound_ids)
                )
                if excluded_compounds_count > 0:
                    message_logs["excluded_compounds_info"] = (
                        f"{excluded_compounds_count} provided compound ID(s) were not found and excluded."
                    )

            # Step 5: Associate target compounds (both created and existed) with the new collection
            all_target_compound_ids = set(
                created_target_compound_ids + (verified_target_compound_ids or [])
            )
            compounds_to_add_total = len(all_target_compound_ids)
            if compounds_to_add_total > 0:
                for target_compound_id in all_target_compound_ids:
                    new_target_compound_in_target_collection = TargetCompoundInTargetCollection(
                        target_compound_id=target_compound_id,
                        target_collection_id=new_target_collection.target_collection_id,
                    )
                    session.add(new_target_compound_in_target_collection)

                message_logs["added_compounds_info"] = (
                    f"{compounds_to_add_total} compound{' was' if compounds_to_add_total == 1 else 's were'} added to the target collection."
                )
            else:
                error_message = f"No compounds were added to the target collection '{new_target_collection_name}'."
                message_logs["added_compounds_info"] = error_message
                raise ValueError(error_message)

            # Step 6: Associate the new target collection with specified sample batches and store the affected batches compounds
            if sample_batch_ids and len(sample_batch_ids) > 0:
                # add all affected batches to the rematch set
                affected_batches_to_rematch.update(sample_batch_ids)

                # Get compounds for each affected batch before saving to db the new collection and new compounds/batches associations
                affected_batches_compounds_before_create = await get_batches_compounds(
                    affected_batches_to_rematch
                )

                batches_to_add_total = len(affected_batches_to_rematch)
                if batches_to_add_total > 0:
                    for sample_batch_id in affected_batches_to_rematch:
                        new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
                            target_collection_id=new_target_collection.target_collection_id,
                            sample_batch_id=sample_batch_id,
                        )
                        session.add(new_target_collection_in_sample_batch)
                    message = f"Target collection '{new_target_collection_name}' was added to  {batches_to_add_total} sample batch{'' if batches_to_add_total == 1 else 'es'}."
                    message_logs["added_to_batches_info"] = message
                else:
                    message = f"The target collection '{new_target_collection_name}' was not added to any batches."
                    message_logs["added_to_batches_info"] = message

            # Step 7: Commit the transaction to the database
            await session.commit()
            await session.refresh(new_target_collection)

        # Step 8: Handle the rematch of sample batches if necessary
        # Get the rematch data for the batches affected by changes in tne new collection compounds/batches associations
        rematch_batches_data = []
        if affected_batches_to_rematch:
            # Get compounds for each affected batch after saving to db the new collection and new compounds/batches associations
            affected_batches_compounds_after_create = await get_batches_compounds(
                affected_batches_to_rematch
            )

            # Compare compounds for affected batches
            affected_batches_rematch_data = await compare_batches_compounds(
                affected_batches_compounds_before_create,
                affected_batches_compounds_after_create,
            )

            rematch_batches_data = affected_batches_rematch_data

            # add all affected batches to the reload set
            sample_batches_to_reload.update(affected_batches_to_rematch)

        # Check if there's any data to process for rematch
        if rematch_batches_data:
            # get the rematched sample batches
            rematched_batches = {
                rematch_batch.sample_batch_id for rematch_batch in rematch_batches_data
            }
            # Exclude rematched batches from reload set since rematch_batches operation will reload the batches
            sample_batches_to_reload -= rematched_batches

            # Create a RematchBatchesBody instance
            rematch_batches_body = RematchBatchesBody(
                sample_batches=rematch_batches_data
            )

            # Add the rematch task to background tasks
            background_tasks.add_task(rematch_batches, rematch_batches_body, sid)

        # Step 9: Emit reload events for affected batches and inform clients about collection changes
        # We have excluded the batches that have been rematched since they will be reloaded as part of rematch process
        if sample_batches_to_reload:
            # Reload the affected sample batches where collection was added but no rematch was needed
            for sample_batch_id in sample_batches_to_reload:
                await sio.emit(
                    "sample_batch_reload",
                    room=sample_batch_id,
                    namespace="/",
                )

        # Emit global target reload event to inform all clients.
        await sio.emit("targets_all_reload", namespace="/")

        # Step 10: Return the new target collection
        # Ensure new target collection is returned with updated associations
        async with async_session() as session:
            stmt = (
                select(TargetCollection)
                .options(
                    joinedload(TargetCollection.sample_batch),
                    joinedload(TargetCollection.target_compound),
                )
                .where(
                    TargetCollection.target_collection_id
                    == new_target_collection.target_collection_id
                )
            )
            result = await session.execute(stmt)
            new_target_collection_with_associations = (
                result.unique().scalar_one_or_none()
            )
        if not new_target_collection_with_associations:
            raise NotFoundException(
                f"Target collection with ID {new_target_collection.target_collection_id} not found"
            )

        return {
            "new_target_collection": new_target_collection_with_associations,
            "message_logs": message_logs,
        }
    except Exception as e:
        api_exc = process_exception(
            e, f"Failed to create target collection '{new_target_collection_name}'"
        )
        raise ApiException(
            api_exc.user_message, api_exc.tech_message, api_exc.status_code
        )


async def update_target_collection(
    target_collection_id: str,
    target_collection_update_body: TargetCollectionUpdateBody,
    background_tasks: BackgroundTasks,
    sid=None,
) -> dict:
    """
    Based on the provided changes this function updates a target collection's basic fields and modifies its associated sample batches or target compounds.

    The function handles these updates separately to reflect the user interface design where target compounds are managed within
    the target collection update UI, and sample batches are managed through a separate modal for managing target collection batches.
    This separation is reflected in the code structure and the Pydantic model.

    Steps:
    1. Unpacks the update payload and initializes control variables.
    2. Fetches the current state of the target collection from the database.
    3. Create new target compounds if any are provided in the update payload.
    4. Verify the existence of provided target compound IDs associations in the database and log any excluded compounds.
    5. Commbinde created and verified target compounds IDs
    6. Determine if changes to associated sample batches or target compounds require a rematch.
    7. Update the target collection's basic fields, and associate it with the provided target compounds and sample batches.
    8. Fetches the rematch data for the batches affected by changes in target_collection/sample_batches asoosiations, if any.
    9. Fetches the rematch data for the batches affected by changes in target_collection/target_compounds asoosiations, if any.
    10. Emits reload events for affected batches and informs clients about collection changes.
    11. Return a summary of the update operation, including the updated target collection with associations  and logs of significant events during the update process.


    :param target_collection_id: The ID of the target collection to be updated.
    :type target_collection_id: str
    :param target_collection_update_body: The updated data for the target collection.
    :type target_collection_update_body: TargetCollectionUpdateBody
    :param background_tasks:  FastAPI background tasks for asynchronous execution of long-running operations like rematching.
    :type background_tasks: BackgroundTasks
    :param sid: Session ID, used for emitting notifications to specific clients, defaults to None.
    :type sid: str, optional
    :raises NotFoundException:  If the target collection with the given ID is not found.
    :raises ApiException: For handling and encapsulating exceptions occurred during the update process.
    :return: A dictionary containing the updated target collection object and a log of messages related to the update process.
    :rtype: dict
    """
    try:
        # Step 1. Initialize control variables and unpack the update payload, reference as _update

        # Initialize set of all batches ids that needs a sio reload emit and flag to trigger targets reload
        sample_batches_to_reload = set()
        targets_all_reload = False
        message_logs = {}
        # Unpack update fields
        target_collection_name_update = (
            target_collection_update_body.target_collection_name
        )
        sample_batches_update = (
            target_collection_update_body.sample_batch_ids
            if target_collection_update_body.sample_batch_ids is not None
            else None
        )
        target_compounds_update = (
            target_collection_update_body.target_compound_ids
            if target_collection_update_body.target_compound_ids
            else None
        )
        target_compounds_to_create = (
            target_collection_update_body.target_compounds_create
            if target_collection_update_body.target_compounds_create
            else None
        )

        # Step 2. Fetch the existing target collection data, reference as existing_
        async with async_session() as session:
            # Retrieves the current state of the target_collection from the database.
            stmt = (
                select(TargetCollection)
                .options(
                    joinedload(TargetCollection.sample_batch),
                    joinedload(TargetCollection.target_compound),
                )
                .where(TargetCollection.target_collection_id == target_collection_id)
            )
            result = await session.execute(stmt)
            existing_target_collection = result.unique().scalar_one_or_none()
            if not existing_target_collection:
                raise NotFoundException(
                    f"Target collection with ID {target_collection_id} not found"
                )

            existing_sample_batches = {
                association.sample_batch_id
                for association in existing_target_collection.sample_batch
            }
            existing_target_compounds = {
                association.target_compound_id
                for association in existing_target_collection.target_compound
            }

            # Step 3: Process and create new target compounds if provided
            created_target_compound_ids = []
            if target_compounds_to_create and len(target_compounds_to_create) > 0:
                try:
                    # Create the target compounds
                    target_compounds_result = await create_target_compound(
                        target_compounds_to_create, session
                    )
                    created_target_compound_ids.extend(
                        target_compounds_result["target_compound_ids"]
                    )
                    message_logs["created_compounds_info"] = target_compounds_result[
                        "message_logs"
                    ]
                except Exception as e:
                    raise RuntimeError(
                        f"Error creating target compound: {str(e)}"
                    ) from e

            # Step 4: Verify that provided target compound ids to associate with collection exists in the database
            verified_target_compound_ids = []
            if target_compounds_update and len(target_compounds_update) > 0:
                stmt = select(TargetCompound.target_compound_id).where(
                    TargetCompound.target_compound_id.in_(target_compounds_update)
                )
                result = await session.execute(stmt)
                existing_compounds = result.scalars().all()
                verified_target_compound_ids = [
                    target_compound_id for target_compound_id in existing_compounds
                ]

                # Log excluded compounds if any
                excluded_compounds_count = len(
                    set(target_compounds_update) - set(verified_target_compound_ids)
                )
                if excluded_compounds_count > 0:
                    message_logs["excluded_compounds_info"] = (
                        f"{excluded_compounds_count} provided compound ID(s) were not found and excluded."
                    )

            # Step 5: Commbinde created and verified target compounds IDs
            all_target_compound_ids = set(
                created_target_compound_ids + verified_target_compound_ids
            )

            # Step 6:  Determine if changes to associated sample batches or target compounds require a rematch.
            # Initialize flags for determining if a there are associations changes and rematch is needed
            changed_compounds = False  # because of changed compounds in collection
            changed_batches = False  # because of changed batches

            if sample_batches_update is not None and (
                set(sample_batches_update) != existing_sample_batches
            ):
                changed_batches = True

                # Get the added and removed batches
                sample_batches_update = set(sample_batches_update)
                added_sample_batches = sample_batches_update - existing_sample_batches
                removed_sample_batches = existing_sample_batches - sample_batches_update

                # Get compounds for each added batch before update
                added_batches_compounds_before_update = await get_batches_compounds(
                    added_sample_batches
                )
                # Get compounds for each removed batch before update
                removed_batches_compounds_before_update = await get_batches_compounds(
                    removed_sample_batches
                )

            if all_target_compound_ids and (
                all_target_compound_ids != existing_target_compounds
            ):
                changed_compounds = True
                added_compounds = all_target_compound_ids - existing_target_compounds
                removed_compounds = existing_target_compounds - all_target_compound_ids

                if added_compounds:
                    compounds_to_add_total = len(added_compounds)
                    message_logs["added_compounds_info"] = (
                        f"{compounds_to_add_total} compound{' was' if compounds_to_add_total == 1 else 's were'} added to the target collection {target_collection_name_update}."
                    )
                if removed_compounds:
                    compounds_to_removed_total = len(removed_compounds)
                    message_logs["removed_compounds_info"] = (
                        f"{compounds_to_removed_total} compound{' was' if compounds_to_removed_total == 1 else 's were'} removed from the target collection {target_collection_name_update}."
                    )

                # Get compounds for each affected batch before update
                affected_batches_compounds_before_update = await get_batches_compounds(
                    existing_sample_batches
                )

            # Step 7: Update the target collection
            # Update basic fields
            update_data = target_collection_update_body.dict(exclude_unset=True)
            for key, value in update_data.items():
                if key in [
                    "target_compound_ids",
                    "sample_batch_ids",
                    "target_compounds_create",
                ]:
                    continue  # Skip sample_batches and target_compounds assosiations as they are handled separately below
                old_value = getattr(existing_target_collection, key)
                setattr(existing_target_collection, key, value)
                if old_value != value:  # field value changed
                    # add all affected batches to the reload set
                    sample_batches_to_reload.update(existing_sample_batches)
                    # set flag to inform clients about target collection basic fields changes
                    targets_all_reload = True

            # Update sample batches associations if any changes in sample batches asoosiations
            if changed_batches:
                # Remove all previous associations
                existing_target_collection.sample_batch.clear()
                # Add new associations
                for sample_batch_id in set(sample_batches_update):
                    new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
                        target_collection_id=existing_target_collection.target_collection_id,
                        sample_batch_id=sample_batch_id,
                    )
                    session.add(new_target_collection_in_sample_batch)

            # Update target compounds associations if any changes in target compounds asoosiations
            if changed_compounds:
                # Remove all previous associations
                existing_target_collection.target_compound.clear()
                # Add new associations
                for target_compound_id in all_target_compound_ids:

                    new_target_compound_in_target_collection = TargetCompoundInTargetCollection(
                        target_compound_id=target_compound_id,
                        target_collection_id=existing_target_collection.target_collection_id,
                    )
                    session.add(new_target_compound_in_target_collection)

            # Save changes to the database
            await session.commit()
            # Refresh the existing_target_collection to update the in-memory instance with the latest state from the database
            await session.refresh(existing_target_collection)
        # Rename for clarity after updates
        updated_target_collection = existing_target_collection

        # Step 8: Get the rematch data for the batches affected by changes in target_collection/sample_batches asoosiations
        rematch_batches_data = []
        if changed_batches:
            # Reload targets to inform about changed collection/batches associations
            targets_all_reload = True
            added_batches_rematch_data = []
            removed_batches_rematch_data = []
            if added_sample_batches:
                # add all added batches to the reload set
                sample_batches_to_reload.update(added_sample_batches)

                # Get compounds for each added batch after update
                added_batches_compounds_after_update = await get_batches_compounds(
                    added_sample_batches
                )
                # Compare compounds for added batches
                added_batches_rematch_data = await compare_batches_compounds(
                    added_batches_compounds_before_update,
                    added_batches_compounds_after_update,
                )

                message = f"Target collection '{target_collection_name_update}' was added to {len(added_sample_batches)} sample batch{'' if len(added_sample_batches) == 1 else 'es'}."
                message_logs["added_to_batches_info"] = message

            if removed_sample_batches:
                # add all removed batches to the reload set
                sample_batches_to_reload.update(removed_sample_batches)

                # Get compounds for each removed batch after update
                removed_batches_compounds_after_update = await get_batches_compounds(
                    removed_sample_batches
                )
                # Compare compounds for removed batches
                removed_batches_rematch_data = await compare_batches_compounds(
                    removed_batches_compounds_before_update,
                    removed_batches_compounds_after_update,
                )

                message = f"Target collection '{target_collection_name_update}' was removed from {len(removed_sample_batches)} sample batch{'' if len(removed_sample_batches) == 1 else 'es'}."
                message_logs["removed_from_batches_info"] = message

            # Combine the results
            rematch_batches_data = (
                added_batches_rematch_data + removed_batches_rematch_data
            )

        # Step 9: Get the rematch data for the batches affected by changes in target_collection/target_compounds asoosiations
        if changed_compounds:
            # Reload targets to inform about changed/created compounds
            targets_all_reload = True
            # Get compounds for each affected batch after update
            affected_batches_compounds_after_update = await get_batches_compounds(
                existing_sample_batches
            )
            # Compare compounds for added batches
            affected_batches_rematch_data = await compare_batches_compounds(
                affected_batches_compounds_before_update,
                affected_batches_compounds_after_update,
            )
            rematch_batches_data = affected_batches_rematch_data

            # add all affected batches to the reload set
            sample_batches_to_reload.update(existing_sample_batches)

        # Check if there's any data to process for rematch
        if rematch_batches_data:
            # get the rematched sample batches
            rematched_batches = {
                rematch_batch.sample_batch_id for rematch_batch in rematch_batches_data
            }
            # Exclude rematched batches from reload set since rematch_batches operation will reload the batches
            sample_batches_to_reload -= rematched_batches

            # Create a RematchBatchesBody instance
            rematch_batches_body = RematchBatchesBody(
                sample_batches=rematch_batches_data
            )

            # Add the rematch task to background tasks
            background_tasks.add_task(rematch_batches, rematch_batches_body, sid)

        # Step 10: Emit reload events for affected batches and inform clients about collection changes

        # We have excluded the batches that have been rematched since they will be reloaded as part of rematch process
        if sample_batches_to_reload:
            # Reload the affected sample batches where collection fields were updated or if some compounds were changed
            for sample_batch_id in sample_batches_to_reload:
                await sio.emit(
                    "sample_batch_reload",
                    room=sample_batch_id,
                    namespace="/",
                )

        # If there are global changes that affect all clients (e.g., changes to collection name, description, etc.),
        # emit an event to inform all clients.
        if targets_all_reload:
            await sio.emit(
                "targets_all_reload",
                namespace="/",
            )

        return {
            "updated_target_collection": updated_target_collection,
            "message_logs": message_logs,
        }
    except Exception as e:
        api_exc = process_exception(
            e, f"Failed to update target collection '{target_collection_name_update}'"
        )
        raise ApiException(
            api_exc.user_message, api_exc.tech_message, api_exc.status_code
        )


async def delete_target_collection(
    target_collection_id: str,
    background_tasks: BackgroundTasks,
    delete_orphan_compounds: bool = False,
    sid=None,
) -> dict:
    """
    Deletes a specified target collection and optionally its orphan compounds, then performs a rematch on affected sample batches.

    The function deletes the target collection from the database and identifies compounds that become orphans as a result of this deletion.
    If specified, these orphan compounds are also deleted. It then proceeds to rematch affected sample batches to ensure data consistency and emits
    necessary reload events.

    Steps:
    1. Verify the existence of the target collection and fetch its associated sample batches and target compounds.
    2. Prepare data for potential rematch operations by fetching associated sample batches and their compounds before deletion.
    3. Identify orphan compounds, if the deletion of such compounds is requested, but postpone their actual deletion.
    4. Delete the target collection from the database and commit the transaction.
    5. Perform rematch operations for sample batches affected by the deletion of the target collection.
    6. Delete identified orphan compounds post-rematch to ensure the rematch process has access to necessary compound data.
    7. Emit reload events for affected sample batches and inform all clients about the deletion.
    8. Construct and return a success message indicating the deletion status and any additional operations performed.

    Note:
        The deletion of orphan compounds is performed after rematching affected batches to ensure the rematch algorithm can access target isotopes
        associated with these compounds. Deleting compounds before committing changes to the database could lead to errors in deleting matches due to
        missing compound data.

    :param target_collection_id: The ID of the target collection to be deleted.
    :type target_collection_id: str
    :param background_tasks: FastAPI background tasks for asynchronous execution of operations like rematching and deletion of orphan compounds.
    :type background_tasks: BackgroundTasks
    :param delete_orphan_compounds: Flag indicating whether orphan compounds should be deleted along with the collection, defaults to False.
    :type delete_orphan_compounds: bool, optional
    :param sid: Session ID, used for emitting notifications to specific client, defaults to None.
    :type sid: str, optional
    :raises NotFoundException: If the target collection with the given ID is not found.
    :raises ApiException: For handling and encapsulating exceptions occurred during the deletion process.
    :return: A dictionary containing a success message and potentially additional information about the deletion process.
    :rtype: dict
    """
    try:
        sample_batches_to_reload = set()
        orphan_compound_ids = []  # List to hold IDs of orphan compounds

        # Step 1. Fetch the  target collection data and verify the existence
        # Retrieves the current state of the target_collection from the database.
        async with async_session() as session:
            stmt = (
                select(TargetCollection)
                .options(
                    joinedload(TargetCollection.sample_batch),
                    joinedload(TargetCollection.target_compound),
                )
                .where(TargetCollection.target_collection_id == target_collection_id)
            )
            result = await session.execute(stmt)
            target_collection = result.unique().scalar_one_or_none()
            if not target_collection:
                raise NotFoundException(
                    f"Target collection with ID {target_collection_id} not found"
                )

            affected_sample_batches = {
                association.sample_batch_id
                for association in target_collection.sample_batch
            }
            collection_target_compounds = {
                association.target_compound_id
                for association in target_collection.target_compound
            }

            # Step 2: Get associated sample batches compounds before deletion for potential rematch
            if affected_sample_batches:
                batches_compounds_before_deletion = await get_batches_compounds(
                    affected_sample_batches
                )

            # Step 3: Identify orphan compoundsif required
            if delete_orphan_compounds and collection_target_compounds:
                # Check if related compounds are present in other collections
                for target_compound_id in collection_target_compounds:
                    other_collections_with_compound = await session.execute(
                        select(TargetCompoundInTargetCollection).filter(
                            TargetCompoundInTargetCollection.target_compound_id
                            == target_compound_id,
                            TargetCompoundInTargetCollection.target_collection_id
                            != target_collection_id,
                        )
                    )

                    # If the compound is not in other collections, delete it
                    if other_collections_with_compound.first() is None:
                        orphan_compound_ids.append(target_compound_id)

            # Step 4: Delete the target collection
            await session.delete(target_collection)
            await session.commit()

        # Step 5: Rematch affected sample batches if necessary
        rematch_batches_data = []
        if affected_sample_batches:
            # add all affected batches to the reload set
            sample_batches_to_reload.update(affected_sample_batches)

            # Re-fetch compounds for each affected batch after deletion
            batches_compounds_after_deletion = await get_batches_compounds(
                affected_sample_batches
            )

            # Compare compounds before and after deletion to determine if a rematch is needed
            affected_batches_rematch_data = await compare_batches_compounds(
                batches_compounds_before_deletion, batches_compounds_after_deletion
            )

            rematch_batches_data = affected_batches_rematch_data

        # Check if there's any data to process for rematch
        if rematch_batches_data:
            # get the rematched sample batches
            rematched_batches = {
                rematch_batch.sample_batch_id for rematch_batch in rematch_batches_data
            }
            # Exclude rematched batches from reload set since rematch_batches operation will reload the batches
            sample_batches_to_reload -= rematched_batches

            # Create a RematchBatchesBody instance
            rematch_batches_body = RematchBatchesBody(
                sample_batches=rematch_batches_data
            )

            # Add the rematch task to background tasks
            background_tasks.add_task(rematch_batches, rematch_batches_body, sid)
            if delete_orphan_compounds and orphan_compound_ids:

                # Step 6: Delete orphan compounds
                for target_compound_id in orphan_compound_ids:
                    background_tasks.add_task(
                        delete_target_compound, target_compound_id
                    )

        # Step 7: Emit reload events for affected batches and inform clients about collection changes
        # Reload the affected sample batches where collection was added but no rematch was needed
        for sample_batch_id in sample_batches_to_reload:
            await sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")
        # Emit global target reload event to inform all clients.
        await sio.emit("targets_all_reload", namespace="/")

        # Step 8: Construct and return success message
        success_message = (
            f"Target collection '{target_collection_id}' deleted successfully."
        )
        if delete_orphan_compounds and orphan_compound_ids:
            success_message += f" Additionally, {len(orphan_compound_ids)} orphan compound{' was' if len(orphan_compound_ids)==1 else 's were'} deleted."

        return {"message": success_message}

    except Exception as e:
        api_exc = process_exception(
            e, f"Failed to delete target collection '{target_collection_id}'"
        )
        raise ApiException(
            api_exc.user_message, api_exc.tech_message, api_exc.status_code
        )
