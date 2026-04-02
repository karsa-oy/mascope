from datetime import datetime, timezone

from sqlalchemy import (
    asc,
    desc,
    func,
    select,
)

from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.api.models.workspace.config import workspace_config
from mascope_backend.api.models.workspace.workspace_pydantic_model import (
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
)
from mascope_backend.db import Workspace, async_session
from mascope_backend.db.id import gen_id
from mascope_backend.socket.records import (
    emit_record_created,
    emit_record_deleted,
    emit_record_updated,
)


@api_controller()
async def get_workspaces(
    workspace_name: str | None = None,
    workspace_type: list[str] | None = None,
    instrument: list[str] | None = None,
    sort: str = "workspace_utc_created",
    order: str = "asc",
    page: int | None = None,
    limit: int | None = None,
) -> dict:
    """
    Retrieves a paginated list of workspaces, optionally sorted by a specified column in either ascending or descending order.

    Steps:
    1. Construct a SQLAlchemy query to select all workspaces.
    2. Apply sorting if specified by the sort and order parameters.
    3. Apply pagination based on the page and limit parameters.
    4. Execute the query to fetch the results.
    5. Convert the results into a list of dictionaries for JSON serialization.

    :param workspace_name: Filter workspaces by name, defaults to None
    :type workspace_name: str | None, optional
    :param workspace_type: Filter workspaces by type (ACQUISITION or ANALYSIS), defaults to None
    :type workspace_type: list[str] | None, optional
    :param instrument: Filter workspaces by instrument associated with the workspace, defaults to None
    :type instrument: list[str] | None, optional
    :param sort: Column to sort by, defaults to "workspace_utc_created"
    :type sort: str, optional
    :param order: Sorting order ('asc' for ascending, 'desc' for descending), defaults to "asc"
    :type order: str, optional
    :param page: Page number for pagination, defaults to None (no pagination).
    :type page: int | None, optional
    :param limit: Number of items per page, defaults to None (no pagination).
    :type limit: int | None, optional
    :return: A dictionary with the total count and a list of workspaces.
    :rtype: dict
    """
    # Validate pagination parameters
    if (page is None) != (limit is None):
        raise ValueError(
            "Both 'page' and 'limit' must be provided together or both omitted."
        )
    async with async_session() as session:
        stmt = select(Workspace)

        # Step 1: Filter by provided parameters
        if workspace_name:
            stmt = stmt.filter(Workspace.workspace_name == workspace_name)

        if workspace_type:
            stmt = stmt.filter(Workspace.workspace_type.in_(workspace_type))

        if instrument:
            stmt = stmt.filter(Workspace.instrument.in_(instrument))

        # Step 2: Apply sorting if specified
        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(Workspace, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(Workspace, sort)))

        # Step 3: Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt)

        # Step 4: Apply pagination
        if page is not None and limit is not None:
            stmt = stmt.offset(page * limit).limit(limit)

        # Step 5: Execute the query
        result = await session.execute(stmt)
        workspaces = result.scalars().all()

    # Step 6: Return the total count and the list of validated workspaces
    return {
        "message": "Workspaces retrieved successfully",
        "results": total,
        "data": [
            WorkspaceRead.model_validate(workspace).model_dump()
            for workspace in workspaces
        ],
    }


@api_controller()
async def get_workspace(workspace_id: str) -> dict:
    """
    Retrieves a single workspace by its unique ID.

    Steps:
    1. Execute a query to fetch the workspace with the specified ID.
    2. Check if the workspace exists. If not, raise a NotFoundException.
    3. Return the workspace's details as a dictionary.

    :param workspace_id: Unique identifier of the workspace to retrieve.
    :type workspace_id: str
    :raises NotFoundException: If the workspace with the given ID is not found.
    :return: The requested workspace's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch workspace by ID
        workspace = await session.get(Workspace, workspace_id)

        if not workspace:
            # Step 2: If workspace not found, raise exception
            raise NotFoundException(f"Workspace with ID '{workspace_id}' not found")

    # Step 3: Return workspace details
    return {
        "message": f"Workspace '{workspace.workspace_name}' retrieved successfully",
        "data": WorkspaceRead.model_validate(workspace).model_dump(),
    }


@api_controller()
async def create_workspace(
    workspace: WorkspaceCreate,
    independent_transaction: bool = False,
) -> dict:
    """
    Creates a new workspace with the specified details.

    Steps:
    1. Create a new Workspace object with the provided details and the generated ID.
    2. Add the new workspace to the session and commit the changes to the database.
    3. Emit a signal to inform clients about the creation of the new workspace.
    4. Return the details of the created workspace.

    :param workspace: Workspace creation details from the request body.
    :type workspace: WorkspaceCreate
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction, defaults to False.
    :type independent_transaction: bool, optional
    :return: The created workspace's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Generate unique ID and create new workspace
        new_workspace = Workspace(
            workspace_id=gen_id(16),
            **workspace.model_dump(),
            locked=(
                1
                if workspace.workspace_type == "ACQUISITION"
                and workspace_config.ACQUISITION_AUTO_LOCK
                else 0
            ),  # Auto-lock acquisition workspaces
            workspace_utc_created=datetime.now(timezone.utc),
        )

        # Step 2: Add to session and commit
        session.add(new_workspace)
        await session.commit()
        await session.refresh(new_workspace)

    # Step 3: Emit creation event to all clients
    workspace_data = WorkspaceRead.model_validate(new_workspace).model_dump()
    if independent_transaction:
        await emit_record_created(
            record_type="workspace",
            record_id=new_workspace.workspace_id,
            record=workspace_data,
        )

    # Step 4: Return the new workspace details
    return {
        "message": f"Workspace '{new_workspace.workspace_name}' created successfully.",
        "data": workspace_data,
    }


@api_controller()
async def update_workspace(
    workspace_id: str,
    workspace_update: WorkspaceUpdate,
    independent_transaction: bool = False,
) -> dict:
    """
    Updates an existing workspace with new data provided in the workspace update request body.

    Steps:
    1. Fetch the existing workspace by its ID from the database.
    2. If the workspace is found, update its properties with the new data provided.
    3. Set the workspace's modification timestamp to the current UTC time.
    4. Commit the updated workspace to the database.
    5. Emit socket.io events to inform clients about the workspace update.

    :param workspace_id: The unique identifier of the workspace to update.
    :type workspace_id: str
    :param workspace_update: The new data for the workspace update.
    :type workspace_update: WorkspaceUpdate
    :param independent_transaction: Flag indicating if operation is independent transaction, defaults to False.
    :type independent_transaction: bool, optional
    :raises NotFoundException: If no workspace is found with the provided ID.
    :return: The updated workspace data as a dictionary.
    :rtype: dict
    """
    # Step 1: Fetch the existing workspace
    async with async_session() as session:
        update_data = workspace_update.model_dump(exclude_unset=True)
        existing_workspace = await session.get(Workspace, workspace_id)
        if not existing_workspace:
            raise NotFoundException(f"Workspace with ID '{workspace_id}' not found")

        # Step 2: Validate ACQUISITION workspace constraints
        if (
            existing_workspace.workspace_type == "ACQUISITION"
            and "workspace_name" in update_data
        ):
            new_name = update_data.get("workspace_name", None)
            instrument = existing_workspace.instrument

            if new_name and not new_name.lower().endswith(instrument.lower()):
                raise ValueError(
                    f"Acquisition workspace name should end with the instrument name. "
                    f"Suggested: '{workspace_config.ACQUISITION_NAME_PREFIX} {instrument}'"
                )

        # Step 3: Update the workspace properties
        for key, value in update_data.items():
            setattr(existing_workspace, key, value)

        # Step 4: Update modification timestamp
        existing_workspace.workspace_utc_modified = datetime.now(timezone.utc)

        # Step 5: Commit the updates
        await session.commit()
        await session.refresh(existing_workspace)

    # Step 6: Emit update event to all clients
    workspace_data = WorkspaceRead.model_validate(existing_workspace).model_dump()
    if independent_transaction:
        await emit_record_updated(
            record_type="workspace",
            record_id=workspace_id,
            record=workspace_data,
        )

    return {
        "message": f"Workspace '{existing_workspace.workspace_name}' updated successfully.",
        "data": workspace_data,
    }


@api_controller()
async def delete_workspace(
    workspace_id: str, independent_transaction: bool = False
) -> dict:
    """
    Deletes a workspace by its unique identifier.

    Steps:
    1. Fetch the workspace by its ID from the database.
    2. If the workspace is found, delete it from the session and commit the changes to the database.
    3. Emit socket.io events to inform clients about the workspace deletion.

    :param workspace_id: The unique identifier of the workspace to delete.
    :type workspace_id: str
    :param independent_transaction: Flag indicating if operation is independent transaction, defaults to False.
    :type independent_transaction: bool, optional
    :raises NotFoundException: If no workspace is found with the provided ID.
    """
    # Step 1: Fetch the workspace
    async with async_session() as session:
        workspace = await session.get(Workspace, workspace_id)
        if not workspace:
            raise NotFoundException(f"Workspace with ID '{workspace_id}' not found")

        # Step 2: Delete the workspace and commit changes
        await session.delete(workspace)
        await session.commit()

    # Step 3: Emit deletion event to all clients
    workspace_name = workspace.workspace_name
    if independent_transaction:
        await emit_record_deleted(
            record_type="workspace",
            record_id=workspace_id,
        )

    return {
        "message": f"Workspace '{workspace_name}' deleted successfully.",
    }
