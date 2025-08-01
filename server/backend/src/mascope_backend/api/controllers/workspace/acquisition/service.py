# pylint: disable=not-callable
from datetime import datetime, timezone
from sqlalchemy import (
    select,
    func,
)
from mascope_backend.socket import sio
from mascope_backend.db import async_session
from mascope_backend.db.id import gen_id
from mascope_backend.db.models import Workspace
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.lib.exceptions.api_exceptions import (
    NotFoundException,
)
from mascope_backend.api.controllers.workspace.workspace_controller import (
    delete_workspace,
    get_workspaces,
)
from mascope_backend.api.models.workspace.workspace_pydantic_model import (
    WorkspaceCreate,
    WorkspaceRead,
)
from mascope_backend.api.models.workspace.config import workspace_config
from mascope_backend.api.new.instruments.service import get_instruments

from mascope_backend.runtime import runtime


@api_controller()
async def get_acquisition_workspace(instrument: str | None) -> dict:
    """
    Retrieve ACQUISITION workspace for the specified instrument.

    Searches for existing ACQUISITION workspace matching the instrument.
    Validates that exactly one workspace exists, logs warning if multiple found.

    :param instrument: Instrument name to find workspace for
    :type instrument: str | None, optional
    :raises NotFoundException: If no ACQUISITION workspace found for instrument
    :return: A dictionary containing ACQUISITION workspace details
    :rtype: dict
    """
    workspaces_data = (
        await get_workspaces(workspace_type=["ACQUISITION"], instrument=[instrument])
    ).get("data", [])

    if not workspaces_data:
        raise NotFoundException(
            f"No ACQUISITION workspace found for instrument '{instrument}'"
        )

    if len(workspaces_data) > 1:
        runtime.logger.warning(
            f"Found {len(workspaces_data)} ACQUISITION workspaces, using first one"
        )

    acquisition_workspace = workspaces_data[0]
    runtime.logger.debug(
        f"Using existing ACQUISITION workspace: {acquisition_workspace['workspace_name']}"
    )

    return {
        "message": f"Acquisition workspace '{acquisition_workspace['workspace_name']}' retrieved successfully",
        "data": WorkspaceRead.model_validate(acquisition_workspace).model_dump(),
    }


@api_controller()
async def create_acquisition_workspaces() -> dict:
    """
    Auto-creates missing ACQUISITION workspaces for all instruments.

    Steps:
    1. Retrieve all available instruments from the system
    2. Validate existing acquisition workspaces (debug check for duplicates)
    3. Query existing ACQUISITION workspaces from database
    4. Identify instruments missing acquisition workspaces
    5. Create new workspaces for missing instruments
    6. Emit socket events to notify clients of changes

    :return: Summary of created workspaces
    :rtype: dict
    """
    # Step 1: Get all available instruments
    if not (
        instruments := [i["instrument"] for i in (await get_instruments())["data"]]
    ):
        message = "No instruments found to create acquisition workspaces"
        runtime.logger.warning(message)
        return {"message": message, "results": 0, "data": []}

    # Step 2: Debug validation - check for duplicate acquisition workspaces per instrument
    async with async_session() as session:
        duplicate_check_stmt = (
            select(
                Workspace.instrument, func.count(Workspace.workspace_id).label("count")
            )
            .where(Workspace.workspace_type == "ACQUISITION")
            .group_by(Workspace.instrument)
            .having(func.count(Workspace.workspace_id) > 1)
        )
        duplicate_result = await session.execute(duplicate_check_stmt)

        if duplicates := duplicate_result.fetchall():
            duplicate_instruments = [row.instrument for row in duplicates]
            runtime.logger.error(
                f"Found duplicate acquisition workspaces for instruments: {duplicate_instruments}. "
                "Each instrument should have only one acquisition workspace."
            )

    # Step 3: Get existing acquisition workspaces
    async with async_session() as session:
        stmt = select(Workspace.instrument).where(
            Workspace.workspace_type == "ACQUISITION"
        )
        result = await session.execute(stmt)
        existing_instruments = set(result.scalars().all())

        # Step 4: Find missing instruments
        if not (missing_instruments := list(set(instruments) - existing_instruments)):
            message = f"All {len(instruments)} instruments have acquisition workspaces"
            runtime.logger.debug(message)
            return {"message": message, "results": 0, "data": []}

        # Step 5: Create missing acquisition workspaces
        created_workspaces = []
        for instrument in missing_instruments:
            workspace_name = f"{workspace_config.ACQUISITION_NAME_PREFIX} {instrument}"

            workspace_data = WorkspaceCreate(
                workspace_name=workspace_name,
                workspace_description=f"Acquisition workspace for {instrument}",
                workspace_type="ACQUISITION",
                instrument=instrument,
            )

            new_workspace = Workspace(
                workspace_id=gen_id(16),
                **workspace_data.model_dump(),
                locked=1 if workspace_config.ACQUISITION_AUTO_LOCK else 0,
                workspace_utc_created=datetime.now(timezone.utc),
            )

            session.add(new_workspace)
            created_workspaces.append(new_workspace)

        await session.commit()

    # Step 6: Emit socket events to notify clients
    if created_workspaces:
        await sio.emit("org_reload", namespace="/")

    message = f"Created {len(created_workspaces)} acquisition workspaces for instruments: {', '.join(missing_instruments)}"
    runtime.logger.debug(message)
    return {
        "message": message,
        "results": len(created_workspaces),
        "data": [
            WorkspaceRead.model_validate(workspace).model_dump()
            for workspace in created_workspaces
        ],
    }


@api_controller()
async def delete_acquisition_workspaces() -> dict:
    """
    Deletes ACQUISITION workspaces for instruments that no longer exist in the system.

    Steps:
    1. Retrieve all current instruments from sample files
    2. Identify workspaces for instruments that no longer exist
    3. Delete orphaned acquisition workspaces

    :return: Summary of deleted workspaces
    :rtype: dict
    """
    # Step 1: Get all current instruments from sample files
    instruments = {i["instrument"] for i in (await get_instruments())["data"]}

    # Step 2: Find orphaned existing acquisition workspaces
    async with async_session() as session:
        to_remove = select(Workspace).where(
            Workspace.workspace_type == "ACQUISITION",
            Workspace.instrument.not_in(instruments),
        )
        orphaned_workspaces = (await session.execute(to_remove)).scalars().all()
        if not orphaned_workspaces:
            message = (
                f"All {len(instruments)} instruments have valid acquisition workspaces."
            )
            runtime.logger.debug(message)
            return {"message": message}

    # Step 3: Delete orphaned acquisition workspaces
    deleted_workspaces = []
    for ws in orphaned_workspaces:
        deleted_workspaces.append(
            {
                "workspace_id": ws.workspace_id,
                "workspace_name": ws.workspace_name,
                "instrument": ws.instrument,
            }
        )
        await delete_workspace(ws.workspace_id)

    deleted_instruments = [ws["instrument"] for ws in deleted_workspaces]
    message = f"Deleted {len(deleted_workspaces)} acquisition workspaces for instruments: {', '.join(deleted_instruments)}"
    runtime.logger.info(message)

    return {
        "message": message,
    }
