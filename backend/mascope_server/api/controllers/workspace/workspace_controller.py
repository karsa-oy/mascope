from datetime import datetime, timezone
from sqlalchemy import (
    select,
    asc,
    desc,
    func,
)
from mascope_server.app import sio
from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.db.models import Workspace
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_server.api.models.workspace.workspace_pydantic_model import (
    WorkspaceCreate,
    WorkspaceUpdate,
)


@api_controller()
async def get_workspaces(
    sort: str = "workspace_utc_created",
    order: str = "asc",
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a paginated list of workspaces, optionally sorted by a specified column in either ascending or descending order.

    Steps:
    1. Construct a SQLAlchemy query to select all workspaces.
    2. Apply sorting if specified by the sort and order parameters.
    3. Apply pagination based on the page and limit parameters.
    4. Execute the query to fetch the results.
    5. Convert the results into a list of dictionaries for JSON serialization.

    :param sort: Column to sort by, defaults to "workspace_utc_created"
    :type sort: str, optional
    :param order: Sorting order ('asc' for ascending, 'desc' for descending), defaults to "asc"
    :type order: str, optional
    :param page: Page number for pagination.
    :type page: int, optional
    :param limit: Number of items per page.
    :type limit: int, optional
    :return: A dictionary with the total count and a list of workspaces.
    :rtype: dict
    """
    async with async_session() as session:
        stmt = select(Workspace)

        # Step 1: Apply sorting if specified
        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(Workspace, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(Workspace, sort)))

        # Step 2: Apply pagination
        stmt = stmt.offset(page * limit).limit(limit)

        # Step 3: Execute the query
        result = await session.execute(stmt)
        workspaces = result.scalars().all()

        # Step 4: Get total count for pagination
        total = await session.scalar(
            select(func.count()).select_from(Workspace)  # pylint: disable=not-callable
        )

    # Step 5: Return the total count and the list of workspaces
    return {"results": total, "data": [workspace.to_dict() for workspace in workspaces]}


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
    return workspace.to_dict()


@api_controller()
async def create_workspace(workspace: WorkspaceCreate) -> dict:
    """
    Creates a new workspace with the specified details.

    Steps:
    1. Create a new Workspace object with the provided details and the generated ID.
    2. Add the new workspace to the session and commit the changes to the database.
    3. Emit a signal to inform clients about the creation of the new workspace.
    4. Return the details of the created workspace.

    :param workspace: Workspace creation details from the request body.
    :type workspace: WorkspaceCreate
    :return: The created workspace's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Generate unique ID and create new workspace
        new_workspace = Workspace(
            workspace_id=gen_id(16),
            workspace_name=workspace.workspace_name,
            workspace_description=workspace.workspace_description,
            workspace_utc_created=datetime.now(timezone.utc),
        )

        # Step 2: Add to session and commit
        session.add(new_workspace)
        await session.commit()
        await session.refresh(new_workspace)

        # Step 3: Emit event
        await sio.emit("org_reload", namespace="/")

    # Step 4: Return the new workspace details
    return new_workspace.to_dict()


@api_controller()
async def update_workspace(workspace_id: str, workspace: WorkspaceUpdate) -> dict:
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
    :param workspace: The new data for the workspace update.
    :type workspace: WorkspaceUpdate
    :raises NotFoundException: If no workspace is found with the provided ID.
    :return: The updated workspace data as a dictionary.
    :rtype: dict
    """
    # Step 1: Fetch the existing workspace
    async with async_session() as session:
        existing_workspace = await session.get(Workspace, workspace_id)
        if not existing_workspace:
            raise NotFoundException(f"Workspace with ID '{workspace_id}' not found")

        # Step 2: Update the workspace properties
        update_data = workspace.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_workspace, key, value)

        # Step 3: Update modification timestamp
        existing_workspace.workspace_utc_modified = datetime.now(timezone.utc)

        # Step 4: Commit the updates
        await session.commit()
        await session.refresh(existing_workspace)

    # Step 5: Emit socket.io events
    await sio.emit("org_reload", namespace="/")
    await sio.emit("workspace_reload", room=workspace_id, namespace="/")

    return existing_workspace.to_dict()


@api_controller()
async def delete_workspace(workspace_id: str):
    """
    Deletes a workspace by its unique identifier.

    Steps:
    1. Fetch the workspace by its ID from the database.
    2. If the workspace is found, delete it from the session and commit the changes to the database.
    3. Emit socket.io events to inform clients about the workspace deletion.

    :param workspace_id: The unique identifier of the workspace to delete.
    :type workspace_id: str
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

    # Step 3: Emit socket.io events
    await sio.emit("org_reload", namespace="/")
    await sio.emit("workspace_reload", room=workspace_id, namespace="/")
