import pandas as pd
import os

from fastapi import HTTPException, BackgroundTasks
from sqlalchemy import (
    asc,
    desc,
    select,
    func,
    literal,
)
from sqlalchemy.orm import joinedload
from typing import List
from datetime import datetime
from backend.db_api_rest import async_session
from backend.server import sio
from lib.peak import detect_peaks, get_peaks
from backend.db.id import gen_id

from ..models.models import (
    Workspace,
    SampleBatch,
    SampleItem,
    TargetCollectionInSampleBatch,
    TargetCollection,
    TargetCompoundInTargetCollection,
    TargetCompound,
    TargetIon,
    IonizationMechanism,
    TargetIsotope,
)
from ..models.pydantic_models.sample_batch_pydantic_model import (
    SampleBatchCreate,
    SampleBatchUpdate,
    SampleBatchCopy,
    SampleBatchExportPeaks,
)
from ..models.pydantic_models.sample_item_pydantic_model import (
    SampleItemCreate,
    SampleItemCopy,
)
from ..models.pydantic_models.calibration_pydantic_model import CalibrationMzFitParams
from ..models.pydantic_models.match_pydantic_model import (
    MatchComputeBatch,
    ProgressProperties,
)
from ..models.exceptions import CustomException
from .match_controller import match_batches_compute
from .sample_items_controller import create_sample_item, copy_sample_item
from .calibration_controller import calibration_mz_calibrate_batch
from .instrument_functions_controller import read_instrument_functions
from .helpers_controller import emit_progress_update


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


async def get_sample_batch(sample_batch_id: str):
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


async def delete_sample_batch(sample_batch_id: str, sid=None):
    try:
        async with async_session() as session:
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

            success_payload = {
                "action": "delete",
                "type": "batch",
                "status": "success",
                "message": f"Batch '{sample_batch.sample_batch_name}' was successfully deleted.",
            }

            await sio.emit(
                "delete_finished",
                success_payload,
                room=sample_batch.workspace_id,
                namespace="/",
            )
            # Notify sid if it has moved from this workspace
            if sid:
                sid_rooms = sio.rooms(sid, namespace="/")
                if sample_batch.workspace_id not in sid_rooms:
                    await sio.emit(
                        "delete_finished", success_payload, room=sid, namespace="/"
                    )

            await sio.emit(
                "workspace_reload", room=sample_batch.workspace_id, namespace="/"
            )

    except Exception as e:
        error_payload = {
            "error": str(e),
            "action": "delete",
            "type": "batch",
            "status": "error",
            "message": f"Deleting batch with ID '{sample_batch_id}' failed",
        }

        # Notify workspace
        await sio.emit(
            "delete_finished",
            error_payload,
            room=sample_batch.workspace_id,
            namespace="/",
        )

        # Notify sid if it has moved from this workspace
        if sid:
            sid_rooms = sio.rooms(sid, namespace="/")
            if sample_batch.workspace_id not in sid_rooms:
                await sio.emit(
                    "delete_finished", error_payload, room=sid, namespace="/"
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
            if key in ["build_params"]:
                # Skip build_params as they are done below
                continue
            setattr(existing_sample_batch, key, value)
        existing_sample_batch.sample_batch_utc_modified = datetime.utcnow()

        # Update the build_params with the stringified versions
        existing_sample_batch.build_params = sample_batch.build_params

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


async def copy_sample_batch(sample_batch_copy: SampleBatchCopy, sid=None):
    try:
        async with async_session() as session:
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

            await session.commit()

        # Copy sample items associated with the original sample batch
        for sample_item in original_sample_batch.sample_item:
            sample_item_copy_data = SampleItemCopy(
                sample_item_id=sample_item.sample_item_id,
                sample_item_name=sample_item.sample_item_name,
                sample_batch_id=new_sample_batch_id,
            )
            await copy_sample_item(
                sample_item_copy=sample_item_copy_data,
            )

        # Notify the workspace where the batch was copied to
        success_payload = {
            "action": "copy",
            "type": "batch",
            "status": "success",
            "message": f"Batch '{sample_batch_copy.sample_batch_name}' was successfully copied to '{workspace.workspace_name}'.",
            "progress_percentage": 100,
        }

        await sio.emit(
            "copy_finished",
            success_payload,
            room=new_sample_batch.workspace_id,
            namespace="/",
        )

        # If SID is provided and not part of the workspace where the batch was copied, notify SID
        if sid:
            sid_rooms = sio.rooms(sid, namespace="/")
            if new_sample_batch.workspace_id not in sid_rooms:
                await sio.emit(
                    "copy_finished", success_payload, room=sid, namespace="/"
                )

        # Reload the workspace where the batch was copied to
        await sio.emit(
            "workspace_reload",
            room=new_sample_batch.workspace_id,
            namespace="/",
        )

    except Exception as e:
        error_message = None
        user_error_message = None
        if isinstance(e, CustomException):
            error_message = e.tech_message
            user_error_message = e.user_message
        else:
            error_message = str(e)

        error_payload = {
            "action": "copy",
            "type": "batch",
            "status": "success",
            "message": f"Coping batch '{sample_batch_copy.sample_batch_name}' failed.",
            "progress_percentage": 100,
        }

        if sid:
            await sio.emit("copy_finished", error_payload, room=sid, namespace="/")

    return new_sample_batch


async def sample_batch_export_peaks(sample_batch: SampleBatchExportPeaks, sid=None):
    try:
        async with async_session() as session:
            # Fetch sample items data
            stmt = select(SampleItem).filter(
                SampleItem.sample_batch_id == sample_batch.sample_batch_id
            )
            result = await session.execute(stmt)
            sample_items_dict_list = [row.to_dict() for row in result.scalars()]
            sample_items_df = pd.DataFrame(sample_items_dict_list)

        peak_data = []
        total_samples = len(sample_items_df)
        item_weight = 1 // total_samples

        for index, row in sample_items_df.iterrows():
            progress_properties = ProgressProperties(
                progress_type="export_peaks",
                total_samples=total_samples,
                item_weight=item_weight,
                item_index=index,
                sid=sid if sid is not None else None,
            )

            try:
                filename = row["filename"]
                instrument_functions = await read_instrument_functions(filename)

                await emit_progress_update(
                    progress_properties=progress_properties, increment=0.1
                )

                sample_file = await detect_peaks(
                    filename, instrument_functions, u_list=None, if_exists="append"
                )

                await emit_progress_update(
                    progress_properties=progress_properties, increment=0.9
                )

                peak_data_item = get_peaks(sample_file, "area").sum(dim="time")

                await emit_progress_update(
                    progress_properties=progress_properties, increment=1
                )
            except Exception as e:
                print(repr(e))
                continue

            peak_data.extend(
                [
                    (
                        sample_batch.sample_batch_name,
                        row["sample_item_name"],
                        row["sample_item_type"],
                        row["filter_id"],
                        row["filename"],
                        peak.mz.item(),
                        peak.item(),
                    )
                    for peak in peak_data_item
                ]
            )

        batch_peak_df = pd.DataFrame.from_records(
            peak_data,
            columns=(
                "batch name",
                "sample name",
                "sample type",
                "filter id",
                "filename",
                "mz",
                "intensity",
            ),
        )

        dt_str = (
            datetime.now().isoformat().replace("-", "").replace(":", "").split(".")[0]
        )

        peakfile_path = os.environ.get("MASCOPE_PRIVATE_DATADIR", ".")
        peakfile_filename = (
            dt_str
            + "_peaks_"
            + sample_batch.sample_batch_name.replace(" ", "_")
            + ".parquet"
        )
        print(f"Writing peak data to file {peakfile_filename}")
        batch_peak_df.to_parquet(
            os.path.join(peakfile_path, peakfile_filename), index=False
        )
        print("Write complete")

        success_payload = {
            "action": "export",
            "type": "peaks",
            "status": "success",
            "message": f"Peak data export for batch '{sample_batch.sample_batch_name}' completed successfully.",
            "progress_percentage": 100,
        }

        if sid:
            await sio.emit(
                "batch_export_peak_data_finished",
                success_payload,
                room=sid,
                namespace="/",
            )

    except Exception as e:
        error_payload = {
            "action": "export",
            "type": "peaks",
            "status": "error",
            "message": f"Peak data export for batch '{sample_batch.sample_batch_name}' failed.",
            "error": str(e),
            "progress_percentage": 100,
        }

        if sid:
            await sio.emit(
                "batch_export_peak_data_finished",
                error_payload,
                room=sid,
                namespace="/",
            )


async def get_batch_targets(sample_batch_id: str, ion_mechanisms: List[str]):
    async with async_session() as session:
        #   TargetCollections
        # Fetch TargetCollections associated with the sample_batch_id
        target_collections = await session.execute(
            select(
                TargetCollection,
                literal(0).label("selection"),
            )
            .join(
                TargetCollectionInSampleBatch,
                TargetCollectionInSampleBatch.target_collection_id
                == TargetCollection.target_collection_id,
            )
            .filter(TargetCollectionInSampleBatch.sample_batch_id == sample_batch_id)
        )
        target_collections = target_collections.scalars().all()

        # Fetch the required target_collection_ids
        target_collection_ids = [tc.target_collection_id for tc in target_collections]

        #   TargetCompounds
        # Fetch TargetCompounds associated with the fetched TargetCollections and add the associated target_collection_id
        target_compounds_query = await session.execute(
            select(TargetCompound)
            .join(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_compound_id
                == TargetCompound.target_compound_id,
            )
            .filter(
                TargetCompoundInTargetCollection.target_collection_id.in_(
                    [tc.target_collection_id for tc in target_collections]
                )
            )
        )
        target_compounds = target_compounds_query.scalars().all()

        associations_list = []

        associations = await session.execute(
            select(
                TargetCompoundInTargetCollection.target_compound_id,
                TargetCompoundInTargetCollection.target_collection_id,
            ).filter(
                TargetCompoundInTargetCollection.target_collection_id.in_(
                    target_collection_ids
                )
            )
        )

        for association in associations:
            compound_id = association.target_compound_id
            collection_id = association.target_collection_id
            associations_list.append((compound_id, collection_id))

        # Convert target_compounds to a dictionary for faster lookup
        target_compounds_dict_lookup = {
            tc.target_compound_id: tc for tc in target_compounds
        }

        target_compounds_dict = []
        for compound_id, collection_id in associations_list:
            tc = target_compounds_dict_lookup.get(compound_id)
            if tc:
                target_compounds_dict.append(
                    {
                        **tc.to_dict(),
                        "target_collection_id": collection_id,
                        "selection": 0,
                    }
                )

        #   TargetIons
        # Fetch TargetIons associated with the fetched TargetCompounds, ion_mechanisms, and relevant TargetCollections
        target_ions_query = await session.execute(
            select(TargetIon)
            .distinct(TargetIon.target_ion_id)
            .join(
                TargetCompoundInTargetCollection,
                TargetIon.target_compound_id
                == TargetCompoundInTargetCollection.target_compound_id,
            )
            .join(
                IonizationMechanism,
                TargetIon.ionization_mechanism_id
                == IonizationMechanism.ionization_mechanism_id,
            )
            .filter(
                TargetCompoundInTargetCollection.target_collection_id.in_(
                    target_collection_ids
                ),
                TargetIon.target_compound_id.in_(
                    [tc.target_compound_id for tc in target_compounds]
                ),
                IonizationMechanism.ionization_mechanism_id.in_(ion_mechanisms),
            )
        )
        target_ions = target_ions_query.scalars().all()

        # Create a lookup dictionary for target_compound_id -> target_collection_id
        target_compound_to_collection = {
            tc["target_compound_id"]: tc["target_collection_id"]
            for tc in target_compounds_dict
        }

        # Fetch all ionization mechanisms and create a lookup dictionary for them
        ion_mechanisms_query = await session.execute(
            select(
                IonizationMechanism.ionization_mechanism_id,
                IonizationMechanism.ionization_mechanism,
            )
        )
        ion_mechanisms_associations = {
            im.ionization_mechanism_id: im.ionization_mechanism
            for im in ion_mechanisms_query
        }

        # Create TargetIons dictionary including the new fields
        target_ions_dict = [
            {
                **ti.to_dict(),
                "target_collection_id": target_compound_to_collection.get(
                    ti.target_compound_id
                ),
                "ionization_mechanism": ion_mechanisms_associations.get(
                    ti.ionization_mechanism_id
                ),
                "selection": 0,
            }
            for ti in target_ions
        ]
        #   TargetIsotopes
        # Fetch TargetIsotopes associated with the fetched TargetIons
        target_isotopes = await session.execute(
            select(
                TargetIsotope,
                literal(0).label("selection"),
            ).filter(
                TargetIsotope.target_ion_id.in_(
                    [ti.target_ion_id for ti in target_ions]
                )
            )
        )
        target_isotopes = target_isotopes.scalars().all()

        return {
            "target_collections_count": len(target_collections),
            "target_compounds_count": len(target_compounds),
            "target_ions_count": len(target_ions),
            "target_isotopes_count": len(target_isotopes),
            "target_collections": [
                tc.to_dict(include_selection=True) for tc in target_collections
            ],
            "target_compounds": target_compounds_dict,
            "target_ions": target_ions_dict,
            "target_isotopes": [
                ti.to_dict(include_selection=True) for ti in target_isotopes
            ],
        }
