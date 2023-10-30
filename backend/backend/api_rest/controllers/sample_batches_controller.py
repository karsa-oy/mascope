from fastapi import HTTPException, BackgroundTasks, status
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime
from backend.db_api_rest import async_session
from backend.server import sio
from backend.db.id import gen_id

from ..models.models import SampleBatch, TargetCollectionInSampleBatch, Workspace
from ..models.pydantic_models.sample_batch_pydantic_model import (
    SampleBatchCreate,
    SampleBatchUpdate,
    SampleBatchCopy,
)
from ..models.pydantic_models.sample_item_pydantic_model import (
    SampleItemCreate,
    SampleItemCopy,
)
from ..models.pydantic_models.calibration_pydantic_model import CalibrationMzFitParams
from ..models.pydantic_models.match_pydantic_model import (
    MatchComputeBatch,
)
from .match_controller import match_batches_compute
from .sample_items_controller import create_sample_item, copy_sample_item
from .calibration_controller import calibration_mz_calibrate_batch


async def get_sample_batches(
    workspace_id: str, sort: str, order: str, page: int, limit: int
):
    async with async_session() as session:
        stmt = select(SampleBatch)

        if workspace_id:
            stmt = stmt.filter(SampleBatch.workspace_id == workspace_id)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(SampleBatch, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(SampleBatch, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        sample_batches = result.scalars().all()

        return {
            "results": total,
            "data": [sample_batch.to_dict() for sample_batch in sample_batches],
        }


async def get_sample_batch_by_id(sample_batch_id: str):
    async with async_session() as session:
        stmt = select(SampleBatch).filter(
            SampleBatch.sample_batch_id == sample_batch_id
        )
        result = await session.execute(stmt)
        sample_batch = result.scalars().first()

        if not sample_batch:
            raise HTTPException(
                status_code=404,
                detail=f"SampleBatch with ID {sample_batch_id} not found",
            )

        return sample_batch.to_dict()


async def create_sample_batch(sample_batch: SampleBatchCreate):
    async with async_session() as session:
        new_sample_batch = SampleBatch(
            sample_batch_id=gen_id(16),
            workspace_id=sample_batch.workspace_id,
            sample_batch_name=sample_batch.sample_batch_name,
            sample_batch_description=sample_batch.sample_batch_description,
            build_params=sample_batch.build_params,
            filter_params=sample_batch.filter_params,
            sample_batch_utc_created=datetime.utcnow(),
        )
        session.add(new_sample_batch)
        await session.commit()
        await session.refresh(new_sample_batch)

        # associations to target collections
        for target_collection_id in sample_batch.target_collection_id:
            new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
                target_collection_id=target_collection_id,
                sample_batch_id=new_sample_batch.sample_batch_id,
            )
            session.add(new_target_collection_in_sample_batch)
        await session.commit()

        # emit the event to inform the clients about the new workspace
        await sio.emit(
            "workspace_reload", room=sample_batch.workspace_id, namespace="/"
        )

        return new_sample_batch


async def delete_sample_batch(sample_batch_id: str):
    async with async_session() as session:
        try:
            result = await session.execute(
                select(SampleBatch).filter(
                    SampleBatch.sample_batch_id == sample_batch_id
                )
            )
            sample_batch = result.scalar_one_or_none()
            if not sample_batch:
                # TODO_error_handling the HTTPException will not work for BackgroundTasks, use sio or other error handling logic
                print(f"Sample batch with ID {sample_batch_id} not found")
                raise ValueError(f"Sample batch with ID {sample_batch_id} not found")

            await session.delete(sample_batch)
            await session.commit()
            await sio.emit(
                "workspace_reload", room=sample_batch.workspace_id, namespace="/"
            )
            await sio.emit(
                "delete_finished",
                {
                    "action": "delete",
                    "type": "batch",
                    "status": "success",
                    "message": f"Batch '{sample_batch.sample_batch_name}' was successfully deleted.",
                },
                room=sample_batch.workspace_id,
                namespace="/",
            )

        except Exception as e:
            await sio.emit(
                "delete_finished",
                {
                    "error": str(e),
                    "action": "delete",
                    "type": "batch",
                    "status": "error",
                    "message": f"Deleting batch with ID '{sample_batch_id}' failed",
                },
                room=sample_batch.workspace_id,
                namespace="/",
            )


async def update_sample_batch(
    sample_batch_id: str,
    sample_batch: SampleBatchUpdate,
    background_tasks: BackgroundTasks,
):
    async with async_session() as session:
        stmt = (
            select(SampleBatch)
            .options(joinedload(SampleBatch.target_collection))
            .where(SampleBatch.sample_batch_id == sample_batch_id)
        )
        result = await session.execute(stmt)
        existing_sample_batch = result.scalars().first()
        if not existing_sample_batch:
            raise HTTPException(status_code=404, detail="Sample batch not found")

        # Determine whether a rematch is needed
        rematch = False
        if set(sample_batch.build_params["ion_mechanisms"]) != set(
            existing_sample_batch.build_params["ion_mechanisms"]
        ):
            rematch = True
        if set(sample_batch.target_collection_id) != {
            item.target_collection_id
            for item in existing_sample_batch.target_collection
        }:
            rematch = True

        # Update the existing sample batch
        update_data = sample_batch.dict(exclude_unset=True)
        for key, value in update_data.items():
            if key in ["build_params", "filter_params"]:
                # Skip build_params and filter_params for now as they are done below
                continue
            setattr(existing_sample_batch, key, value)
        existing_sample_batch.sample_batch_utc_modified = datetime.utcnow()

        # Update the build_params and filter_params with the stringified versions
        existing_sample_batch.build_params = sample_batch.build_params
        existing_sample_batch.filter_params = sample_batch.filter_params

        # Update target collections associations
        if "target_collection_id" in update_data:
            # Remove all previous associations
            existing_sample_batch.target_collection.clear()
            # Add new associations
            for target_collection_id in sample_batch.target_collection_id:
                new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
                    target_collection_id=target_collection_id,
                    sample_batch_id=existing_sample_batch.sample_batch_id,
                )
                session.add(new_target_collection_in_sample_batch)

        await session.commit()
    # Inform clients about the update
    if rematch:
        background_tasks.add_task(
            match_batches_compute,
            [MatchComputeBatch(sample_batch_id=existing_sample_batch.sample_batch_id)],
        )
    else:
        await sio.emit(
            "workspace_reload",
            room=existing_sample_batch.workspace_id,
            namespace="/",
        )

    return existing_sample_batch


async def autosampler_import_batch(
    sample_batch, sample_items, params: CalibrationMzFitParams, background_tasks
):
    created_sample_items = []

    for sample_item in sample_items:
        sample_item_model = SampleItemCreate(**sample_item)
        created_item = await create_sample_item(sample_item_model, skipReload=True)
        created_sample_items.append(created_item.to_dict())

    background_tasks.add_task(
        process_batch,
        sample_batch,
        created_sample_items,
        params,
    )


async def process_batch(sample_batch, sample_items, params):
    sample_batch_id = sample_batch.get("sample_batch_id")

    # Step 1. Calibrate batch
    try:
        calibration_results = await calibration_mz_calibrate_batch(
            sample_batch, sample_items, params
        )
    except Exception as e:
        print("Failed to calibrate batch %s" % sample_batch["sample_batch_name"])
        print(e)

    # Step 2. Compute matches for the batch
    try:
        await match_batches_compute(
            [MatchComputeBatch(sample_batch_id=sample_batch_id)]
        )
    except Exception as e:
        print(
            "Failed to compute matched for batch %s" % sample_batch["sample_batch_name"]
        )
        print(e)

    # Step 3. Send the warning notification if calibration was failed and information about samples
    failed_samples = [
        sample
        for sample in calibration_results
        if sample["status"] == "calibration failed"
    ]
    if failed_samples:
        await sio.emit(
            "calibration_mz_calibrate_batch_failed",
            {"type": "failed_calibration_samples", "samples": failed_samples},
            room=sample_batch["sample_batch_id"],
            namespace="/",
        )
    return


async def copy_sample_batch(sample_batch_copy: SampleBatchCopy):
    async with async_session() as session:
        try:
            # Check if the provided workspace_id exists
            workspace = await session.get(Workspace, sample_batch_copy.workspace_id)

            if not workspace:
                error_message = (
                    f"Workspace with ID {sample_batch_copy.workspace_id} not found"
                )
                print(error_message)
                raise ValueError(error_message)

            # Fetch the original sample batch with related TargetCollectionInSampleBatch and SampleItem records
            stmt = (
                select(SampleBatch)
                .options(
                    joinedload(SampleBatch.target_collection),
                    joinedload(SampleBatch.sample_item),
                )
                .filter(
                    SampleBatch.sample_batch_id == sample_batch_copy.sample_batch_id
                )
            )
            result = await session.execute(stmt)
            original_sample_batch = result.scalars().first()

            if not original_sample_batch:
                error_message = f"Sample batch with ID {sample_batch_copy.sample_batch_id} not found"
                print(error_message)
                raise ValueError(error_message)

            # Create new sample batch record with a new ID, name, description, workspace and time of creation, but copy all other data
            new_sample_batch_id = gen_id(16)
            new_sample_batch_data = {
                c.name: getattr(original_sample_batch, c.name)
                for c in SampleBatch.__table__.columns
                if c.name != "sample_batch_id"
            }
            new_sample_batch_data.update(
                {
                    "sample_batch_id": new_sample_batch_id,
                    "workspace_id": sample_batch_copy.workspace_id,
                    "sample_batch_name": sample_batch_copy.sample_batch_name,
                    "sample_batch_description": sample_batch_copy.sample_batch_description,
                    "sample_batch_utc_created": datetime.utcnow(),
                }
            )
            new_sample_batch = SampleBatch(**new_sample_batch_data)
            session.add(new_sample_batch)

            # Copy TargetCollectionInSampleBatch records associated with the original sample batch
            for target_collection in original_sample_batch.target_collection:
                new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
                    target_collection_id=target_collection.target_collection_id,
                    sample_batch_id=new_sample_batch_id,
                )
                session.add(new_target_collection_in_sample_batch)

            # Copy sample items associated with the original sample batch
            for sample_item in original_sample_batch.sample_item:
                sample_item_copy_data = SampleItemCopy(
                    sample_item_id=sample_item.sample_item_id,
                    sample_item_name=sample_item.sample_item_name,
                    sample_batch_id=new_sample_batch_id,
                )
                await copy_sample_item(
                    sample_item_copy=sample_item_copy_data,
                    session=session,
                )

            await session.commit()

            rooms_to_notify = [
                new_sample_batch.workspace_id,
                original_sample_batch.workspace_id,
            ]
            # Notify clients the copy process has finished
            for room in rooms_to_notify:
                await sio.emit(
                    "copy_batch_finished",
                    {
                        "action": "copy",
                        "type": "batch",
                        "message": f"Batch '{sample_batch_copy.sample_batch_name}' was successfully copied.",
                        "progress_percentage": 100,
                    },
                    room=room,
                    namespace="/",
                )

            # Emit event to inform clients
            await sio.emit(
                "workspace_reload",
                room=new_sample_batch.workspace_id,
                namespace="/",
            )

        except Exception as e:
            # Notify clients of an error
            for room in rooms_to_notify:
                await sio.emit(
                    "copy_batch_failed",
                    {
                        "error": str(e),
                        "action": "copy",
                        "type": "batch",
                        "message": f"Copy batch '{sample_batch_copy.sample_batch_name}' failed",
                        "progress_percentage": 100,
                    },
                    room=room,
                    namespace="/",
                )

        return new_sample_batch
