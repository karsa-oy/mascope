import asyncio

from backend.server import sio
from backend.db.id import gen_id

from fastapi import HTTPException, BackgroundTasks
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import joinedload

from backend.db_api_rest import async_session
from backend.api.match import match_batch_compute
from .target_compounds_controller import delete_target_compound, create_target_compound
from .target_compound_in_target_collection_controller import (
    create_target_compound_in_target_collection,
    delete_target_compound_in_target_collection,
)
from ..controllers.target_collection_in_sample_batch_controller import (
    create_target_collection_in_sample_batch,
)
from ..controllers.sample_batches_controller import (
    compute_sample_batch_matches,
)
from ..models.models import (
    SampleBatch,
    TargetCollection,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
)
from ..models.pydantic_models.target_collection_pydantic_model import (
    TargetCollectionCreate,
    TargetCollectionUpdate,
)
from ..models.pydantic_models.target_compound_in_target_collection_pydantic_model import (
    TargetCompoundInTargetCollectionBase,
)
from ..models.pydantic_models.target_collection_in_sample_batch_pydantic_model import (
    TargetCollectionInSampleBatchBase,
)
from ..models.pydantic_models.sample_batch_pydantic_model import (
    SampleBatchComputeMatch,
)


async def get_target_collections(sort: str, order: str, page: int, limit: int):
    async with async_session() as session:
        stmt = select(TargetCollection)

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


async def get_target_collection_by_id(target_collection_id: str):
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
    target_collection: TargetCollectionCreate, background_tasks: BackgroundTasks
):
    async with async_session() as session:
        sample_batches_to_rematch = []
        message_logs = {}

        new_target_collection = TargetCollection(
            target_collection_id=gen_id(16),
            target_collection_name=target_collection.target_collection_name,
            target_collection_description=target_collection.target_collection_description,
        )
        session.add(new_target_collection)

        # Check if target_compounds are provided
        if (
            target_collection.target_compounds
            and len(target_collection.target_compounds) > 0
        ):
            try:
                # Create the target compounds
                target_compounds_result = await create_target_compound(
                    target_collection.target_compounds, session
                )
            except Exception as e:
                raise RuntimeError(f"Error creating target compound: {str(e)}") from e

            target_compound_ids = target_compounds_result["target_compound_ids"]

            # Add the target compounds to the target collection
            target_compounds_in_target_collection = [
                TargetCompoundInTargetCollectionBase(
                    target_compound_id=target_compound_id,
                    target_collection_id=new_target_collection.target_collection_id,
                )
                for target_compound_id in target_compound_ids
            ]

            added_target_compounds_in_target_collection = (
                await create_target_compound_in_target_collection(
                    target_compounds_in_target_collection, session
                )
            )
            # Add added_compounds_info to message_logs
            if len(added_target_compounds_in_target_collection) > 0:
                add_compound_logs = {}
                number_added = 0

                for i, status_log in added_target_compounds_in_target_collection[
                    "message_logs"
                ].items():
                    add_compound_logs[i] = status_log
                    if status_log["status_code"] == 201:
                        number_added += 1

                message_logs[
                    "added_compounds_info"
                ] = f"{number_added} compound{' was' if number_added == 1 else 's were'} added to the target collection."

                message_logs["added_compounds_logs"] = add_compound_logs
            else:
                message_logs[
                    "added_compounds_info"
                ] = "No compounds were added to the target collection."

        # Add the target collection to the sample batches
        if (
            target_collection.sample_batches
            and len(target_collection.sample_batches) > 0
        ):
            target_collections_in_sample_batch = [
                TargetCollectionInSampleBatchBase(
                    target_collection_id=new_target_collection.target_collection_id,
                    sample_batch_id=sample_batch.sample_batch_id,
                )
                for sample_batch in target_collection.sample_batches
            ]
            result = await create_target_collection_in_sample_batch(
                target_collections_in_sample_batch, False, None, session
            )
            added_collections_to_sample_batch = result[
                "added_collections_to_sample_batch"
            ]
            if (
                added_collections_to_sample_batch
                and len(added_collections_to_sample_batch) > 0
            ):
                sample_batches_to_rematch.extend(target_collection.sample_batches)

                added_to_batches_logs = {}
                number_added = 0

                for i, status_log in result["message_logs"].items():
                    added_to_batches_logs[i] = status_log
                    if status_log["status_code"] == 201:
                        number_added += 1

                message_logs[
                    "added_to_batches_info"
                ] = f"{len(target_collection.sample_batches)} sample batch{' was' if len(target_collection.sample_batches) == 1 else 'es were'} added to the target collection."

                message_logs["added_to_batches_logs"] = added_to_batches_logs

        else:
            message_logs[
                "added_to_batches_info"
            ] = "The target collection was not added to any batches."

        # Add the new target collection to the session and commit
        await session.commit()

        # Run rematch for all sample batches in the list
        # TODO_match
        if sample_batches_to_rematch:
            background_tasks.add_task(
                compute_sample_batch_matches, sample_batches_to_rematch
            )

        await sio.emit(
            "targets_all_reload",
            namespace="/",
        )

        return {
            "new_target_collection": new_target_collection,
            "created_compounds_count": len(
                target_compounds_result["created_compounds"]
            ),
            "created_compounds": target_compounds_result["created_compounds"],
            "existing_compounds_count": len(
                target_compounds_result["existing_compounds"]
            ),
            "existing_compounds": target_compounds_result["existing_compounds"],
            "message_logs": message_logs,
        }


async def delete_target_collection(
    target_collection_id: str,
    background_tasks: BackgroundTasks,
    delete_orphan_compounds: bool = False,
):
    async with async_session() as session:
        # Check if the target collection exists
        result = await session.execute(
            select(TargetCollection).filter(
                TargetCollection.target_collection_id == target_collection_id
            )
        )
        target_collection = result.scalar_one_or_none()

        if not target_collection:
            raise HTTPException(status_code=404, detail="Target collection not found")

        # Get all associated sample batches with their workspace_ids
        sample_batches = await session.execute(
            select(
                TargetCollectionInSampleBatch.sample_batch_id,
                SampleBatch.workspace_id,
            )
            .join(
                SampleBatch,
                TargetCollectionInSampleBatch.sample_batch_id
                == SampleBatch.sample_batch_id,
            )
            .filter(
                TargetCollectionInSampleBatch.target_collection_id
                == target_collection_id
            )
        )

        sample_batches_to_rematch = [sb for sb in sample_batches]
        workspaces_to_reload = set([sb[1] for sb in sample_batches_to_rematch])

        if delete_orphan_compounds:
            # Check if the compound is present in other collections
            compounds_in_collection = await session.execute(
                select(TargetCompoundInTargetCollection).filter(
                    TargetCompoundInTargetCollection.target_collection_id
                    == target_collection_id
                )
            )

            for compound in compounds_in_collection.scalars():
                other_collections_with_compound = await session.execute(
                    select(TargetCompoundInTargetCollection).filter(
                        TargetCompoundInTargetCollection.target_compound_id
                        == compound.target_compound_id,
                        TargetCompoundInTargetCollection.target_collection_id
                        != target_collection_id,
                    )
                )

                # If the compound is not in other collections, delete it
                if other_collections_with_compound.first() is None:
                    await delete_target_compound(compound.target_compound_id, session)

        # Delete the target collection
        await session.delete(target_collection)
        await session.commit()

        # Run rematch for all sample batches in the list
        # TODO_match
        if sample_batches_to_rematch:
            sample_batches = [
                SampleBatchComputeMatch(sample_batch_id=sb[0], workspace_id=sb[1])
                for sb in sample_batches_to_rematch
            ]

            background_tasks.add_task(compute_sample_batch_matches, sample_batches)

            for workspace_id in workspaces_to_reload:
                await sio.emit("targets_all_reload", room=workspace_id, namespace="/")


async def update_target_collection(
    target_collection_id, target_collection_update: TargetCollectionUpdate = None
):
    added_compounds = []
    removed_compounds = []
    sample_batches_to_reload = set()
    sample_batches_to_rematch = set()
    message_logs = {}

    async with async_session() as session:
        # Fetching the target collection
        target_collection = await session.execute(
            select(TargetCollection).where(
                TargetCollection.target_collection_id == target_collection_id
            )
        )
        target_collection = target_collection.scalar_one_or_none()

        if not target_collection:
            raise HTTPException(
                status_code=404,
                detail=f"Target collection not found. ID: {target_collection_id}",
            )

        # Get all affected sample batches
        sample_batches = await session.execute(
            select(TargetCollectionInSampleBatch.sample_batch_id).where(
                TargetCollectionInSampleBatch.target_collection_id.in_(
                    [target_collection_id]
                )
            )
        )
        sample_batches_ids = {sb[0] for sb in sample_batches}

        # Updating basic fields
        if target_collection_update:
            update_data = target_collection_update.dict(exclude_unset=True)
            update_info = {}
            for key, value in update_data.items():
                if key not in ["compounds_to_add", "compounds_to_remove"]:
                    old_value = getattr(target_collection, key)
                    setattr(target_collection, key, value)
                    if old_value != value:  # field value changed
                        update_info[key] = f"{old_value} -> {value}"

            if update_info:
                message_logs["update_info"] = update_info
                sample_batches_to_reload.update(sample_batches_ids)
            else:
                message_logs["update_info"] = "No changes in the name and description."
        else:
            message_logs[
                "collection_update_info"
            ] = "No updates were provided for name and description."

        if (
            target_collection_update
            and target_collection_update.compounds_to_add
            and len(target_collection_update.compounds_to_add) > 0
        ):
            # Add target_collection_id to each compound in the compounds_to_add list
            for compound_to_add in target_collection_update.compounds_to_add:
                compound_to_add.target_collection_id = target_collection_id

            result = await create_target_compound_in_target_collection(
                target_collection_update.compounds_to_add, session
            )
            add_compound_logs = {}
            number_added = 0
            for i, status_log in result["message_logs"].items():
                add_compound_logs[i] = status_log
                if status_log["status_code"] == 201:
                    added_compounds.append(target_collection_update.compounds_to_add[i])
                    number_added += 1
                    sample_batches_to_rematch.update(sample_batches_ids)

            message_logs[
                "added_compounds_info"
            ] = f"{number_added} compound{' was' if number_added == 1 else 's were'} added to the target collection."

            message_logs["added_compounds_logs"] = add_compound_logs
        else:
            message_logs[
                "added_compounds_info"
            ] = "No compounds were added to the target collection."

        # Compounds removal logic
        if (
            target_collection_update
            and target_collection_update.compounds_to_remove
            and len(target_collection_update.compounds_to_remove) > 0
        ):
            remove_compounds_errors = []  # Initialize error list
            for compound_to_remove in target_collection_update.compounds_to_remove:
                try:
                    await delete_target_compound_in_target_collection(
                        compound_to_remove.target_compound_id,
                        target_collection_id,
                        session,
                    )
                    removed_compounds.append(compound_to_remove)
                    sample_batches_to_reload.update(sample_batches_ids)
                except HTTPException as e:
                    remove_compounds_errors.append(e.detail)

            if len(remove_compounds_errors) > 0:
                message_logs[
                    "remove_compounds_error"
                ] = "Errors occurred while removing the compounds: " + "; ".join(
                    remove_compounds_errors
                )

            if len(removed_compounds) > 0:
                message_logs[
                    "removed_compounds"
                ] = f"{len(removed_compounds)} compound{' was' if len(removed_compounds) == 1 else 's were'} removed from the target collection."
        else:
            message_logs[
                "removed_compounds"
            ] = "No compounds were removed from the target collection."

        # Committing changes
        await session.commit()

        # Rematch the affected sample batches compounds were added
        for sample_batch_id in sample_batches_to_rematch:
            # FIX replace with request
            # TODO_background Use the fastApi background tasks
            task = asyncio.create_task(match_batch_compute(None, sample_batch_id))
            await task

        # Exclude rematched ids since they've been reloaded
        sample_batches_to_reload = sample_batches_to_reload - sample_batches_to_rematch

        # Reload the affected sample batches where collection fields were updated or if some compounds were removed
        for sample_batch_id in sample_batches_to_reload:
            await sio.emit(
                "sample_batch_reload",
                room=sample_batch_id,
                namespace="/",
            )

        return {
            "updated_target_collection": target_collection,
            "added_compounds": added_compounds,
            "removed_compounds": removed_compounds,
            "message_logs": message_logs,
        }
