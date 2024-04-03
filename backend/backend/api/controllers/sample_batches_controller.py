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
from backend.db import async_session
from backend.api_sio import sio
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
    SampleBatchCreateBody,
    SampleBatchUpdateBody,
    SampleBatchCopyBody,
    SampleBatchExportPeaks,
)
from ..models.pydantic_models.calibration_pydantic_model import CalibrationMzFitParams
from ..models.pydantic_models.match_pydantic_model import (
    RematchBatchBody,
    ProgressProperties,
)
from .match_controller import rematch_batch
from .target_compounds_controller import get_target_compounds
from .sample_items_controller import create_sample_item, copy_sample_item
from .calibration_controller import calibration_mz_calibrate_batch
from .instrument_functions_controller import read_instrument_functions
from .helpers_controller import emit_progress_update
from ..exceptions import process_exception, ApiException, NotFoundException


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


async def get_batch_targets(
    sample_batch_id: str,
    alarms_list: List[str] = ["TARGETS"],
):
    async with async_session() as session:
        # Retrieve the sample details
        stmt = select(SampleBatch).filter(
            SampleBatch.sample_batch_id == sample_batch_id
        )
        result = await session.execute(stmt)
        sample_batch = result.scalars().first()

        if not sample_batch:
            raise HTTPException(
                status_code=404,
                detail=f"Sample batch with ID {sample_batch_id} not found",
            )

        # get the batch ion_mechanisms
        build_params = sample_batch.build_params
        ion_mechanisms = build_params["ion_mechanisms"]

        #   TargetCollections
        # Fetch TargetCollections associated with the sample_batch_id
        target_collections = await session.execute(
            select(
                TargetCollection,
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

        target_collections_dict = []
        for collection in target_collections:
            # Set the alarm_mode based on collection type
            target_collections_dict.append(
                {
                    **collection.to_dict(),
                    # Determine alarm_mode based on collection type and alarms_list
                    "alarm_mode": collection.target_collection_type in alarms_list,
                    "selection": 0,
                }
            )

        # Create a lookup dictionary for collection alarm_mode
        collection_alarm_mode_lookup = {
            collection["target_collection_id"]: collection["alarm_mode"]
            for collection in target_collections_dict
        }

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
                        "alarm_mode": collection_alarm_mode_lookup.get(
                            collection_id, False
                        ),
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
        target_compound_to_collections = {}
        for compound_id, collection_id in associations_list:
            if compound_id in target_compound_to_collections:
                target_compound_to_collections[compound_id].append(collection_id)
            else:
                target_compound_to_collections[compound_id] = [collection_id]

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
        target_ions_dict = []
        for ti in target_ions:
            # Get all target_collection_ids for the current ion's compound
            collection_ids = target_compound_to_collections.get(
                ti.target_compound_id, []
            )
            # Create a separate entry for each collection the ion's compound belongs to
            for collection_id in collection_ids:
                target_ions_dict.append(
                    {
                        **ti.to_dict(),
                        "target_collection_id": collection_id,
                        "alarm_mode": collection_alarm_mode_lookup.get(
                            collection_id, False
                        ),
                        "ionization_mechanism": ion_mechanisms_associations.get(
                            ti.ionization_mechanism_id
                        ),
                        "selection": 0,
                    }
                )
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

        # Create a lookup dictionary for target_ion_id -> list of target_collection_ids
        target_ion_to_collections = {}
        for ti in target_ions_dict:
            ion_id = ti["target_ion_id"]
            collection_id = ti["target_collection_id"]
            if ion_id in target_ion_to_collections:
                target_ion_to_collections[ion_id].add(collection_id)
            else:
                target_ion_to_collections[ion_id] = {collection_id}

        # Now use this lookup to create TargetIsotopes dictionary
        target_isotopes_dict = []
        for isotope in target_isotopes:
            # Get all target_collection_ids for the current isotope's ion
            collection_ids = list(
                target_ion_to_collections.get(isotope.target_ion_id, [])
            )
            # Create a separate entry for each collection the isotope's ion belongs to
            for collection_id in collection_ids:
                target_isotopes_dict.append(
                    {
                        **isotope.to_dict(),
                        "target_collection_id": collection_id,
                        "alarm_mode": collection_alarm_mode_lookup.get(
                            collection_id, False
                        ),
                        "selection": 0,
                    }
                )

        data = {
            "target_collections_count": len(target_collections_dict),
            "target_compounds_count": len(target_compounds_dict),
            "target_ions_count": len(target_ions_dict),
            "target_isotopes_count": len(target_isotopes_dict),
            "target_collections": target_collections_dict,
            "target_compounds": target_compounds_dict,
            "target_ions": target_ions_dict,
            "target_isotopes": target_isotopes_dict,
        }

        return {
            "message": "Batch targets are fetched successfully.",
            "data": data,
        }


async def create_sample_batch(sample_batch: SampleBatchCreateBody) -> SampleBatch:
    try:
        async with async_session() as session:
            new_sample_batch = SampleBatch(
                sample_batch_id=gen_id(16),
                workspace_id=sample_batch.workspace_id,
                sample_batch_name=sample_batch.sample_batch_name,
                sample_batch_description=sample_batch.sample_batch_description,
                build_params=sample_batch.build_params.dict(),
                sample_batch_utc_created=datetime.utcnow(),
            )
            session.add(new_sample_batch)
            await session.commit()
            await session.refresh(new_sample_batch)

            # associations to target collections
            for target_collection_id in sample_batch.target_collection_ids:
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
    except Exception as e:
        api_exc = process_exception(
            e,
            f"Failed to create sample batch '{sample_batch.sample_batch_name}'",
        )
        raise ApiException(
            api_exc.user_message, api_exc.tech_message, api_exc.status_code
        )


async def update_sample_batch(
    sample_batch_id: str,
    sample_batch_update_body: SampleBatchUpdateBody,
    background_tasks: BackgroundTasks,
) -> SampleBatch:
    """
    Updates the specified sample batch with new information and associations. It checks for changes in associated target collections
    and ionization mechanisms to determine if a rematch of the sample batch is necessary. If so, it prepares and executes the rematch
    process using background tasks. The function also handles the update of basic information like the batch name and description,
    and emits appropriate events to notify clients of changes.

    Steps:
    1. Fetch the existing sample batch data.
    2. Determine if a rematch is needed based on changes in collections or ionization mechanisms.
    3. Update the basic information of the sample batch and its associations with target collections.
    4. If needed, prepare and execute the rematch, identifying added or removed compounds and ionization mechanisms.
    5. Based on the updates, emit workspace reload or a sample batch reload.

    :param sample_batch_id: ID of the sample batch to be updated.
    :type sample_batch_id: str
    :param sample_batch_update_body: Updated data for the sample batch.
    :type sample_batch_update_body: SampleBatchUpdateBody
    :param background_tasks: Background tasks for asynchronous execution.
    :type background_tasks: BackgroundTasks
    :raises NotFoundException: Raised if the sample batch is not found in the database.
    :raises ApiException: For handling any exceptions that occur during the update process.
    :return: The updated SampleBatch object, reflecting the changes made.
    rtype: SampleBatch
    """
    try:
        # Flags for determining if a rematch batch is needed
        rematch_compounds = False  # because of changed collections => compounds
        rematch_ion_mechanisms = False  # because of changed ion_mechanisms
        targets_all_reload = False

        # Flags for determining if a reload is needed
        workspace_reload = False  # if name is changed
        sample_batch_reload = False  # if other basic fields changed and no rematch

        # Step 1. Fetch the existing sample batch data, reference as existing_
        # Retrieves the current state of the sample batch from the database.
        async with async_session() as session:
            stmt = (
                select(SampleBatch)
                .options(joinedload(SampleBatch.target_collection))
                .where(SampleBatch.sample_batch_id == sample_batch_id)
            )
            result = await session.execute(stmt)
            existing_sample_batch = result.unique().scalar_one_or_none()
            if not existing_sample_batch:
                raise NotFoundException(
                    f"Sample batch with ID {sample_batch_id} not found"
                )

            # Step 2: Determine if a rematch is needed based on changes in collections or ion mechanisms
            # Checks for changes in collections and ionization mechanisms.
            new_collections = set(sample_batch_update_body.target_collection_ids)
            existing_collections = {
                item.target_collection_id
                for item in existing_sample_batch.target_collection
            }
            existing_ion_mechanisms = set(
                existing_sample_batch.build_params["ion_mechanisms"]
            )
            new_ion_mechanisms = set(
                sample_batch_update_body.build_params.ion_mechanisms
            )

            # Check if target_compounds were added/remoced
            if new_collections != existing_collections:
                rematch_compounds = True

                # Fetch and store the existing sample batch compounds
                batch_compounds_result = await get_target_compounds(
                    sample_batch_id=sample_batch_id
                )
                existing_compounds = set(
                    tc["target_compound_id"] for tc in batch_compounds_result["data"]
                )

            # Check if ion_mechanisms were added/remoced
            if new_ion_mechanisms != existing_ion_mechanisms:
                rematch_ion_mechanisms = True

            # Step 3: Update the sample batch.
            # Applies the updates to the sample batch and commits to the database.
            update_data = sample_batch_update_body.dict(exclude_unset=True)
            for key, value in update_data.items():
                if key in ["build_params", "target_collection_ids"]:
                    continue  # Skip build_params and target_collections assosiations as they are handled separately below
                if key in ["sample_batch_name"]:
                    old_name = getattr(existing_sample_batch, key)
                    if old_name != value:  # name value changed
                        # set flag to inform clients about sample batch basic fields changes (emit workspace reload event)
                        workspace_reload = True
                if key in ["sample_batch_description"]:
                    old_description = getattr(existing_sample_batch, key)
                    if old_description != value:  # description value changed
                        # set flag to reload batch
                        sample_batch_reload = True
                setattr(existing_sample_batch, key, value)

            existing_sample_batch.sample_batch_utc_modified = datetime.utcnow()

            # Update build_params and associations with target collections
            existing_sample_batch.build_params = (
                sample_batch_update_body.build_params.dict()
            )

            if "target_collection_ids" in update_data:
                targets_all_reload = True
                # Remove all previous associations
                existing_sample_batch.target_collection.clear()
                # Add new associations
                for target_collection_id in new_collections:
                    new_target_collection_in_sample_batch = (
                        TargetCollectionInSampleBatch(
                            target_collection_id=target_collection_id,
                            sample_batch_id=existing_sample_batch.sample_batch_id,
                        )
                    )
                    session.add(new_target_collection_in_sample_batch)
            # Save changes to the database
            await session.commit()
            await session.refresh(existing_sample_batch)
        # Rename for clarity after updates
        updated_sample_batch = existing_sample_batch

        # Step 4: Prepare and execute rematch if needed
        # Calculates the changes in compounds and ion mechanisms and prepares the data for rematch.
        if rematch_compounds or rematch_ion_mechanisms:
            # Initialize parameters for rematching
            added_target_compound_ids = set()
            added_ionization_mechanism_ids = set()
            removed_target_compound_ids = set()
            removed_ionization_mechanism_ids = set()
            # batch/workspace reload will be done in the end of rematching process
            sample_batch_reload = False

            # Calculate added and removed compounds and ionization mechanisms
            if rematch_compounds:
                # Fetch the enew current sample batch compounds
                batch_compounds_result = await get_target_compounds(
                    sample_batch_id=sample_batch_id
                )
                current_compounds = set(
                    tc["target_compound_id"] for tc in batch_compounds_result["data"]
                )

                added_target_compound_ids = current_compounds - existing_compounds
                removed_target_compound_ids = existing_compounds - current_compounds
            if rematch_ion_mechanisms:
                # Fetch the new current sample batch data
                async with async_session() as session:
                    stmt = (
                        select(SampleBatch)
                        .options(joinedload(SampleBatch.target_collection))
                        .where(SampleBatch.sample_batch_id == sample_batch_id)
                    )
                    result = await session.execute(stmt)
                    current_sample_batch = result.scalars().first()

                current_ion_mechanisms = set(
                    current_sample_batch.build_params["ion_mechanisms"]
                )

                added_ionization_mechanism_ids = (
                    current_ion_mechanisms - existing_ion_mechanisms
                )
                removed_ionization_mechanism_ids = (
                    existing_ion_mechanisms - current_ion_mechanisms
                )

            # prepare data for rematching
            rematch_body = RematchBatchBody(
                sample_batch_id=sample_batch_id,
                workspace_id=updated_sample_batch.workspace_id,
                added_target_compound_ids=list(added_target_compound_ids),
                removed_target_compound_ids=list(removed_target_compound_ids),
                added_ionization_mechanism_ids=list(added_ionization_mechanism_ids),
                removed_ionization_mechanism_ids=list(removed_ionization_mechanism_ids),
                independent_transaction=True,
                progress_properties=ProgressProperties(
                    progress_type="rematch_batch",
                    workspace_reload=workspace_reload,
                ),
            )
            # Set workspace_reload flag to False, since the reload will happen in rematch process
            workspace_reload = False

            # create backfround task for batch rematching
            background_tasks.add_task(
                rematch_batch,
                rematch_body.sample_batch_id,
                rematch_body.workspace_id,
                rematch_body.added_target_compound_ids,
                rematch_body.added_ionization_mechanism_ids,
                rematch_body.removed_target_compound_ids,
                rematch_body.removed_ionization_mechanism_ids,
                rematch_body.independent_transaction,
                rematch_body.progress_properties,
            )

        # Step 5: Based on the updates, emit workspace reload or a sample batch reload.
        if workspace_reload:
            # Emit workspace reload event if the name has changed
            await sio.emit(
                "workspace_reload",
                room=updated_sample_batch.workspace_id,
                namespace="/",
            )
        if sample_batch_reload:
            # Emit batch reload event if the description has changed and rematch was not needed
            await sio.emit(
                "sample_batch_reload",
                room=updated_sample_batch.sample_batch_id,
                namespace="/",
            )
        # If there are  changes in samle_batches associations emit an event to inform all clients.
        if targets_all_reload:
            await sio.emit(
                "targets_all_reload",
                namespace="/",
            )
        return updated_sample_batch
    except Exception as e:
        api_exc = process_exception(
            e,
            f"Failed to update sample batch '{sample_batch_update_body.sample_batch_name}'",
        )
        raise ApiException(
            api_exc.user_message, api_exc.tech_message, api_exc.status_code
        )


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


async def import_sample_items(
    sample_batch_id: str,
    sample_items,
    params: CalibrationMzFitParams,
    calibrate_batch: bool = True,
):
    """
    Imports a sample items to specified batch by creating provided sample items, calibrating the batch, computing matches, and handling errors.

    Steps:
    1. Create provided sample items and save them to the database.
    2. Optionally calibrate the batch using the provided calibration parameters, based on the calibrate_batch flag.
    3. Compute matches for the batch.
    4. In case of calibration failure, send a notification with information about failed samples.

    :param sample_batch_id: ID of the sample batch where sample items will be imported.
    :type sample_batch_id: str
    :param sample_items: List of sample items to be created and imported.
    :type sample_items: List[SampleItemCreate]
    :param params: Calibration parameters to be used for the batch.
    :type params: CalibrationMzFitParams
    :raises ApiException: Raised for any exceptions that occur during the import process.
    """
    try:
        # Step 1. Create provided sample items and save to database
        for sample_item in sample_items:
            await create_sample_item(sample_item, skipReload=True)

        # Step 2. Optionally calibrate batch if calibrate_batch is True (default behaviour)
        if calibrate_batch:
            calibration_results = await calibration_mz_calibrate_batch(
                sample_batch_id, params
            )

        # Step 3. Compute matches for the batch
        progress_properties = ProgressProperties(
            progress_type="rematch_batch",
        )

        await rematch_batch(
            sample_batch_id=sample_batch_id,
            independent_transaction=False,
            progress_properties=progress_properties,
        )

    # TODO_error_handling for background tasks we emit the sio with payload, should similar to http response structure
    except ApiException as e:
        # Step 4. Send the warning notification if calibration was failed and information about samples
        context_message = f"Failed to import sample items to batch '{sample_batch_id}'"
        api_exc = process_exception(e, context_message)
        user_error_message = api_exc.user_message
        detail = api_exc.tech_message

        error_payload = {
            "action": "import",
            "type": "samples",
            "status": "error",
            "message": user_error_message,  # should be "error" as in http responses
            "error": detail,  # should be "detail" as in http responses
            "progress_percentage": 100,
        }

        # TODO_notifications refactor failed_calibration_samples notificationsm
        # Check the failed calibrations samples
        failed_samples = [
            sample
            for sample in calibration_results
            if sample["status"] == "calibration failed"
        ]

        if failed_samples:
            error_payload["failed_calibration_samples":failed_samples]

        await sio.emit(
            "import_samples_to_batch_finished",
            error_payload,
            room=sample_batch_id,
            namespace="/",
        )


async def copy_sample_batch(
    sample_batch_id: str,
    workspace_id: str,
    sample_batch_name: str,
    sample_batch_description: str,
    sid=None,
):
    """
    Copies a sample batch, including its associated sample items and target collections, into a specified workspace with a new name and description.
    The function ensures all related entities like sample items and target collections are also copied over to maintain the integrity of the sample batch data.
    Called as a background task from the endpoint, so it also handles sio notification and workspace reloading upon successful copying or if any errors occur.

    Steps:
    1. Validate the workspace into which the sample batch is being copied.
    2. Fetch and validate the original sample batch from the database.
    3. Create a new sample batch with updated information and copy all other data.
    4. Copy TargetCollectionInSampleBatch records associated with the original sample batch.
    5. Commit the new sample batch to the database.
    6. Copy associated sample items from the original to the new sample batch.
    7. Notify the workspace where the batch was copied and handle workspace reloading.

    :param sample_batch_id: ID of the original sample batch to be copied.
    :type sample_batch_id: str
    :param workspace_id: ID of the workspace where the new sample batch will be placed.
    :type workspace_id: str
    :param sample_batch_name: Name for the new copied sample batch.
    :type sample_batch_name: str
    :param sample_batch_description: Description for the new copied sample batch.
    :type sample_batch_description: str
    :param sid: Session ID, used for emitting notifications to specific clients, defaults to None.
    :type sid: str, optional
    :raises NotFoundException: If the workspace or original sample batch is not found.
    """
    try:
        async with async_session() as session:
            # Step 1: Validate the workspace into which the sample batch is being copied.
            workspace = await session.get(Workspace, workspace_id)

            if not workspace:
                raise NotFoundException(f"Workspace with ID {workspace_id} not found")

            # Step 2: Fetch and validate the original sample batch from the database with related TargetCollectionInSampleBatch and SampleItem records
            stmt = (
                select(SampleBatch)
                .options(
                    joinedload(SampleBatch.target_collection),
                    joinedload(SampleBatch.sample_item),
                )
                .filter(SampleBatch.sample_batch_id == sample_batch_id)
            )
            result = await session.execute(stmt)
            original_sample_batch = result.scalars().first()

            if not original_sample_batch:
                raise NotFoundException(
                    f"Sample batch with ID {sample_batch_id} not found"
                )

            # Step 3: Create and add to session a new sample batch record with a new ID, name, description, workspace and time of creation, but copy all other data
            new_sample_batch_id = gen_id(16)
            new_sample_batch_data = {
                c.name: getattr(original_sample_batch, c.name)
                for c in SampleBatch.__table__.columns
                if c.name != "sample_batch_id"
            }
            new_sample_batch_data.update(
                {
                    "sample_batch_id": new_sample_batch_id,
                    "workspace_id": workspace_id,
                    "sample_batch_name": sample_batch_name,
                    "sample_batch_description": sample_batch_description,
                    "sample_batch_utc_created": datetime.utcnow(),
                }
            )
            new_sample_batch = SampleBatch(**new_sample_batch_data)
            session.add(new_sample_batch)

            # Step 4: Copy TargetCollectionInSampleBatch records associated with the original sample batch
            for target_collection in original_sample_batch.target_collection:
                new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
                    target_collection_id=target_collection.target_collection_id,
                    sample_batch_id=new_sample_batch_id,
                )
                session.add(new_target_collection_in_sample_batch)

            # Step 5: Commit the new sample batch to the database
            await session.commit()

        # Step 6: Copy sample items associated with the original sample batch
        for sample_item in original_sample_batch.sample_item:
            await copy_sample_item(
                sample_item_id=sample_item.sample_item_id,
                sample_item_name=sample_item.sample_item_name,
                sample_batch_id=new_sample_batch_id,
            )

        # Step 7: Notify the workspace where the batch was copied and handle workspace reloading.
        success_payload = {
            "action": "copy",
            "type": "batch",
            "status": "success",
            "message": f"Batch '{sample_batch_name}' was successfully copied to '{workspace.workspace_name}'.",
            "progress_percentage": 100,
        }

        await sio.emit(
            "copy_finished",
            success_payload,
            room=workspace_id,
            namespace="/",
        )

        # If SID is provided and not part of the workspace where the batch was copied, notify SID
        if sid:
            sid_rooms = sio.rooms(sid, namespace="/")
            if workspace_id not in sid_rooms:
                await sio.emit(
                    "copy_finished", success_payload, room=sid, namespace="/"
                )

        # Reload the workspace where the batch was copied to
        await sio.emit(
            "workspace_reload",
            room=workspace_id,
            namespace="/",
        )

    # TODO_error_handling for background tasks we emit the sio with payload similar to http response structure
    except Exception as e:
        context_message = f"Failed to copy the sample batch '{sample_batch_name}'"
        api_exc = process_exception(e, context_message)
        user_error_message = api_exc.user_message
        detail = api_exc.tech_message

        error_payload = {
            "action": "copy",
            "type": "batch",
            "status": "error",
            "message": user_error_message,  # should be "error" as in http responses
            "error": detail,  # should be "detail" as in http responses
            "progress_percentage": 100,
        }

        if sid:
            await sio.emit("copy_finished", error_payload, room=sid, namespace="/")

        # Reload the workspace where the batch was copied to if
        if workspace:
            await sio.emit(
                "workspace_reload",
                room=workspace.workspace_id,
                namespace="/",
            )


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

        peakfile_path = os.environ.get("MASCOPE_PRIVATE_INSTRUMENT_DIR", ".")
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
