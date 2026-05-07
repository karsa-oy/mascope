from datetime import datetime, timezone

from sqlalchemy import (
    func,
    select,
)

from mascope_backend.api.controllers.dataset.dataset_controller import (
    delete_dataset,
    get_datasets,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.lib.exceptions.api_exceptions import (
    NotFoundException,
)
from mascope_backend.api.models.dataset.config import dataset_config
from mascope_backend.api.models.dataset.dataset_pydantic_model import (
    DatasetCreate,
    DatasetRead,
)
from mascope_backend.api.new.instruments.service import get_instruments
from mascope_backend.db import Dataset, Workspace, async_session
from mascope_backend.db.id import gen_id
from mascope_backend.runtime import runtime
from mascope_backend.socket.records.service import (
    emit_record_created,
    emit_record_deleted,
)
from mascope_file.name import resolve_instrument_type


@api_controller()
async def get_acquisition_dataset(instrument: str | None) -> dict:
    """
    Retrieve ACQUISITION dataset for the specified instrument.

    Searches for existing ACQUISITION dataset matching the instrument.
    Validates that exactly one dataset exists, logs warning if multiple found.

    :param instrument: Instrument name to find dataset for
    :type instrument: str | None, optional
    :raises NotFoundException: If no ACQUISITION dataset found for instrument
    :return: A dictionary containing ACQUISITION dataset details
    :rtype: dict
    """
    datasets_data = (
        await get_datasets(dataset_type=["ACQUISITION"], instrument=[instrument])
    ).get("data", [])

    if not datasets_data:
        raise NotFoundException(
            f"No ACQUISITION dataset found for instrument '{instrument}'"
        )

    if len(datasets_data) > 1:
        runtime.logger.warning(
            f"Found {len(datasets_data)} ACQUISITION datasets, using first one"
        )

    acquisition_dataset = datasets_data[0]
    runtime.logger.debug(
        f"Using existing ACQUISITION dataset: {acquisition_dataset['dataset_name']}"
    )

    return {
        "message": f"Acquisition dataset '{acquisition_dataset['dataset_name']}' retrieved successfully",
        "data": DatasetRead.model_validate(acquisition_dataset).model_dump(),
    }


@api_controller()
async def create_acquisition_datasets() -> dict:
    """
    Auto-creates missing ACQUISITION datasets for all instruments.

    Steps:
    - Retrieve all available instruments from the system
    - Validate existing acquisition datasets (debug check for duplicates)
    - Query existing ACQUISITION datasets from database
    - Identify instruments missing acquisition datasets
    - Create new datasets for missing instruments
    - Emit socket events to notify clients of changes

    :return: Summary of created datasets
    :rtype: dict
    """
    # --- Get all available instruments ---
    if not (
        instruments := [i["instrument"] for i in (await get_instruments())["data"]]
    ):
        message = "No instruments found to create acquisition datasets"
        runtime.logger.warning(message)
        return {"message": message, "results": 0, "data": []}

    # --- Debug validation - check for duplicate acquisition datasets per instrument ---
    async with async_session() as session:
        duplicate_check_stmt = (
            select(Dataset.instrument, func.count(Dataset.dataset_id).label("count"))
            .where(Dataset.dataset_type == "ACQUISITION")
            .group_by(Dataset.instrument)
            .having(func.count(Dataset.dataset_id) > 1)
        )
        duplicate_result = await session.execute(duplicate_check_stmt)

        if duplicates := duplicate_result.fetchall():
            duplicate_instruments = [row.instrument for row in duplicates]
            runtime.logger.error(
                f"Found duplicate acquisition datasets for instruments: {duplicate_instruments}. "
                "Each instrument should have only one acquisition dataset."
            )

    # --- Get existing acquisition datasets ---
    async with async_session() as session:
        # Resolve the system Acquisitions workspace
        acq_ws_id = (
            await session.execute(
                select(Workspace.workspace_id).where(
                    Workspace.workspace_name == "Acquisitions",
                    Workspace.is_system.is_(True),
                )
            )
        ).scalar_one_or_none()
        if acq_ws_id is None:
            return {
                "message": "System 'Acquisitions' workspace not found",
                "results": 0,
                "data": [],
            }

        stmt = select(Dataset.instrument).where(Dataset.dataset_type == "ACQUISITION")
        result = await session.execute(stmt)
        existing_instruments = set(result.scalars().all())

        # --- Find missing instruments ---
        if not (missing_instruments := list(set(instruments) - existing_instruments)):
            message = f"All {len(instruments)} instruments have acquisition datasets"
            runtime.logger.debug(message)
            return {"message": message, "results": 0, "data": []}

        # --- Create missing acquisition datasets and emit socket events ---
        created_datasets = []
        for instrument in missing_instruments:
            dataset_name = f"{dataset_config.ACQUISITION_NAME_PREFIX} {instrument}"
            dataset_data = DatasetCreate(
                dataset_name=dataset_name,
                dataset_description=f"Acquisition dataset for {instrument}",
                dataset_type="ACQUISITION",
                instrument=instrument,
            )

            new_dataset = Dataset(
                dataset_id=gen_id(16),
                workspace_id=acq_ws_id,
                **dataset_data.model_dump(),
                locked=1 if dataset_config.ACQUISITION_AUTO_LOCK else 0,
                dataset_utc_created=datetime.now(timezone.utc),
            )

            session.add(new_dataset)
            created_datasets.append(new_dataset)

        await session.commit()

    # --- Emit dataset events ---
    created_datasets_data = [
        DatasetRead.model_validate(ws).model_dump() for ws in created_datasets
    ]
    for dataset in created_datasets_data:
        await emit_record_created(
            record_type="dataset",
            record_id=dataset["dataset_id"],
            record=dataset,
        )

    # --- Emit instrument creation events for any new instruments ---
    for instrument in missing_instruments:
        instrument_type = resolve_instrument_type(instrument, throw=False)
        await emit_record_created(
            record_type="instrument",
            record_id=instrument,
            record={
                "instrument": instrument,
                "type": instrument_type,
            },
        )

    message = f"Created {len(created_datasets)} acquisition datasets for instruments: {', '.join(missing_instruments)}"
    runtime.logger.debug(message)
    return {
        "message": message,
        "results": len(created_datasets),
        "data": [
            DatasetRead.model_validate(dataset).model_dump()
            for dataset in created_datasets
        ],
    }


@api_controller()
async def delete_acquisition_datasets() -> dict:
    """
    Deletes ACQUISITION datasets for instruments that no longer exist in the system.

    Steps:
    - Retrieve all current instruments from sample files
    - Identify datasets for instruments that no longer exist
    - Delete orphaned acquisition datasets

    :return: Summary of deleted datasets
    :rtype: dict
    """
    # --- Get all current instruments from sample files ---
    instruments = {i["instrument"] for i in (await get_instruments())["data"]}

    # --- Find orphaned existing acquisition datasets ---
    async with async_session() as session:
        to_remove = select(Dataset).where(
            Dataset.dataset_type == "ACQUISITION",
            Dataset.instrument.not_in(instruments),
        )
        orphaned_datasets = (await session.execute(to_remove)).scalars().all()
        if not orphaned_datasets:
            message = (
                f"All {len(instruments)} instruments have valid acquisition datasets."
            )
            runtime.logger.debug(message)
            return {"message": message}

    # --- Delete orphaned acquisition datasets and emit events ---
    deleted_datasets = []
    deleted_instruments = []
    for ws in orphaned_datasets:
        deleted_datasets.append(
            {
                "dataset_id": ws.dataset_id,
                "dataset_name": ws.dataset_name,
                "instrument": ws.instrument,
            }
        )
        deleted_instruments.append(ws.instrument)

        await delete_dataset(dataset_id=ws.dataset_id, independent_transaction=True)

    # --- Emit instrument deletion events ---
    for instrument in deleted_instruments:
        await emit_record_deleted(
            record_type="instrument",
            record_id=instrument,
        )

    message = f"Deleted {len(deleted_datasets)} acquisition datasets for instruments: {', '.join(deleted_instruments)}"
    runtime.logger.info(message)

    return {
        "message": message,
    }
