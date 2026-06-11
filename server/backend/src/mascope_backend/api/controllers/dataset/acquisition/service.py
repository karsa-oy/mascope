from datetime import datetime, timezone

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.exc import IntegrityError

from mascope_backend.api.controllers.dataset.dataset_controller import (
    delete_dataset,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.models.dataset.config import dataset_config
from mascope_backend.api.models.dataset.dataset_pydantic_model import (
    DatasetRead,
)
from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.api.new.instruments.service import get_instruments
from mascope_backend.db import Dataset, User, Workspace, WorkspaceMember, async_session
from mascope_backend.db.id import gen_id
from mascope_backend.runtime import runtime
from mascope_backend.socket.records.service import (
    emit_record_created,
    emit_record_deleted,
    emit_record_reload,
)
from mascope_file.name import resolve_instrument_type, validate_instrument_name


# Maps global role_id → workspace_role for auto-created system workspaces.
# Only admins and owners are auto-added; guests/editors must be invited.
_role_levels = auth_settings.ROLE_ACCESS_LEVELS
_ROLE_MAP = {
    level: name
    for name, level in _role_levels.items()
    if level >= _role_levels["admin"]
}


async def _ensure_instrument_workspace(
    instrument: str, owner_user_id: int | None = None
) -> str:
    """Get or create the system workspace for an instrument.

    When a new workspace is created, global admins and owners are added
    with matching workspace roles.  If *owner_user_id* is given, that
    user is always assigned the ``owner`` role regardless of their
    global role.  Guests and editors are not auto-added.

    :param instrument: Instrument name
    :param owner_user_id: User who triggered the creation (becomes owner)
    :return: workspace_id of the instrument workspace
    """
    workspace_name = f"{dataset_config.ACQUISITION_NAME_PREFIX} {instrument}"

    async with async_session() as session:
        ws_id = (
            await session.execute(
                select(Workspace.workspace_id).where(
                    Workspace.workspace_name == workspace_name,
                    Workspace.is_system.is_(True),
                )
            )
        ).scalar_one_or_none()

        if ws_id is not None:
            return ws_id

    # Create workspace and seed membership for admins/owners
    ws_id = gen_id(16)
    try:
        async with async_session() as session:
            session.add(
                Workspace(
                    workspace_id=ws_id,
                    workspace_name=workspace_name,
                    workspace_description=f"System workspace for {instrument} acquisitions",
                    workspace_status="active",
                    is_system=True,
                )
            )

            users = (await session.execute(select(User.id, User.role_id))).all()
            added = 0
            for user_id, role_id in users:
                if user_id == owner_user_id:
                    ws_role = "owner"
                else:
                    ws_role = _ROLE_MAP.get(role_id)
                    if ws_role is None:
                        continue
                session.add(
                    WorkspaceMember(
                        workspace_member_id=gen_id(16),
                        workspace_id=ws_id,
                        user_id=user_id,
                        workspace_role=ws_role,
                    )
                )
                added += 1

            await session.commit()
    except IntegrityError:
        # Another worker created the workspace concurrently - fetch its ID.
        async with async_session() as session:
            ws_id = (
                await session.execute(
                    select(Workspace.workspace_id).where(
                        Workspace.workspace_name == workspace_name,
                        Workspace.is_system.is_(True),
                    )
                )
            ).scalar_one()
        runtime.logger.debug(
            f"Workspace '{workspace_name}' created concurrently, reusing {ws_id}"
        )
        return ws_id

    runtime.logger.info(
        f"Created instrument workspace '{workspace_name}' with {added} members"
    )
    await emit_record_reload(record_type="workspace")
    return ws_id


@api_controller()
async def get_acquisition_dataset(
    instrument: str,
    year: int | None = None,
    user_id: int | None = None,
) -> dict:
    """
    Get or create the year-based ACQUISITION dataset for an instrument.

    Looks up the ACQUISITION dataset whose ``instrument`` matches and whose
    ``dataset_name`` equals the requested year (defaults to the current UTC
    year).  If the dataset does not exist it is created together with the
    instrument workspace (if that is also missing).

    :param instrument: Instrument name
    :param year: Calendar year for the dataset (defaults to current UTC year)
    :param user_id: User who triggered the request (becomes workspace owner
        when a new workspace is created)
    :return: dict with ``"data"`` key holding the dataset
    """
    validate_instrument_name(instrument)

    if year is None:
        year = datetime.now(timezone.utc).year
    year_str = str(year)

    # --- Try to find existing year-dataset in the system workspace ---
    workspace_id = await _ensure_instrument_workspace(instrument, owner_user_id=user_id)

    async with async_session() as session:
        dataset = (
            await session.execute(
                select(Dataset)
                .join(Workspace, Workspace.workspace_id == Dataset.workspace_id)
                .where(
                    Dataset.dataset_type == "ACQUISITION",
                    Dataset.instrument == instrument,
                    Dataset.dataset_name == year_str,
                    Dataset.workspace_id == workspace_id,
                    Workspace.is_system.is_(True),
                )
            )
        ).scalar_one_or_none()

    if dataset is not None:
        runtime.logger.debug(
            f"Using existing ACQUISITION dataset: {instrument}/{year_str}"
        )
        return {
            "message": f"Acquisition dataset '{year_str}' retrieved for {instrument}",
            "data": DatasetRead.model_validate(dataset).model_dump(),
        }

    async with async_session() as session:
        new_dataset = Dataset(
            dataset_id=gen_id(16),
            workspace_id=workspace_id,
            dataset_name=year_str,
            dataset_description=f"{year} acquisitions for {instrument}",
            dataset_type="ACQUISITION",
            instrument=instrument,
            locked=1 if dataset_config.ACQUISITION_AUTO_LOCK else 0,
            dataset_utc_created=datetime.now(timezone.utc),
        )
        session.add(new_dataset)
        await session.commit()

    dataset_data = DatasetRead.model_validate(new_dataset).model_dump()
    await emit_record_created(
        record_type="dataset",
        record_id=new_dataset.dataset_id,
        record=dataset_data,
        room=workspace_id,
    )

    instrument_type = resolve_instrument_type(instrument, throw=False)
    await emit_record_created(
        record_type="instrument",
        record_id=instrument,
        record={"instrument": instrument, "type": instrument_type},
    )

    runtime.logger.info(f"Created ACQUISITION dataset '{year_str}' for {instrument}")
    return {
        "message": f"Created acquisition dataset '{year_str}' for {instrument}",
        "data": dataset_data,
    }


@api_controller()
async def create_acquisition_datasets(user_id: int | None = None) -> dict:
    """
    Auto-creates missing per-instrument workspaces and current-year ACQUISITION
    datasets for all instruments that have sample files.

    Steps:
    - Retrieve all known instruments from sample files
    - For each instrument: ensure workspace exists, ensure current-year dataset exists
    - Emit socket events for newly created resources

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

    current_year = datetime.now(timezone.utc).year
    created_datasets = []

    for instrument in instruments:
        result = await get_acquisition_dataset(
            instrument=instrument, year=current_year, user_id=user_id
        )
        # get_acquisition_dataset is get-or-create; collect only newly created ones
        # (We can't easily distinguish here, but the function is idempotent.)
        created_datasets.append(result["data"])

    message = (
        f"Ensured acquisition datasets exist for {len(instruments)} instruments "
        f"(year {current_year})"
    )
    runtime.logger.debug(message)
    return {
        "message": message,
        "results": len(created_datasets),
        "data": created_datasets,
    }


@api_controller()
async def delete_acquisition_datasets() -> dict:
    """
    Deletes ACQUISITION datasets for instruments that no longer exist in the
    system, and removes empty instrument workspaces.

    Steps:
    - Retrieve all current instruments from sample files
    - Identify datasets for instruments that no longer exist
    - Delete orphaned acquisition datasets
    - Delete instrument workspaces that no longer contain any datasets

    :return: Summary of deleted datasets
    :rtype: dict
    """
    # --- Get all current instruments from sample files ---
    instruments = {i["instrument"] for i in (await get_instruments())["data"]}

    # --- Find orphaned existing acquisition datasets ---
    async with async_session() as session:
        to_remove = select(Dataset).where(
            Dataset.dataset_type == "ACQUISITION",
            Dataset.instrument.not_in(instruments)
            if instruments
            else Dataset.dataset_type == "ACQUISITION",
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
    for ds in orphaned_datasets:
        deleted_datasets.append(
            {
                "dataset_id": ds.dataset_id,
                "dataset_name": ds.dataset_name,
                "instrument": ds.instrument,
            }
        )
        if ds.instrument is not None:
            deleted_instruments.append(ds.instrument)

        await delete_dataset(dataset_id=ds.dataset_id, independent_transaction=True)

    # --- Emit instrument deletion events ---
    for instrument in set(deleted_instruments):
        await emit_record_deleted(
            record_type="instrument",
            record_id=instrument,
        )

    # --- Clean up empty instrument workspaces ---
    async with async_session() as session:
        # Find system workspaces that start with the acquisitions prefix
        # and have no remaining datasets
        acq_workspaces = (
            (
                await session.execute(
                    select(Workspace).where(
                        Workspace.workspace_name.like(
                            f"{dataset_config.ACQUISITION_NAME_PREFIX} %"
                        ),
                        Workspace.is_system.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )

        for ws in acq_workspaces:
            ds_count = (
                await session.execute(
                    select(func.count(Dataset.dataset_id)).where(
                        Dataset.workspace_id == ws.workspace_id
                    )
                )
            ).scalar()
            if ds_count == 0:
                await session.delete(ws)
                runtime.logger.info(
                    f"Deleted empty instrument workspace '{ws.workspace_name}'"
                )

        await session.commit()

    message = (
        f"Deleted {len(deleted_datasets)} acquisition datasets for instruments: "
        f"{', '.join(deleted_instruments)}"
    )
    runtime.logger.info(message)

    return {
        "message": message,
    }
