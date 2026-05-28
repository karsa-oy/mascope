from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, select

from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.api.models.dataset.config import dataset_config
from mascope_backend.api.models.dataset.dataset_pydantic_model import (
    DatasetCreate,
    DatasetRead,
    DatasetUpdate,
)
from mascope_backend.api.new.workspaces.exceptions import (
    WorkspaceNotFoundException,
)
from mascope_backend.db import Dataset, Workspace, async_session
from mascope_backend.db.id import gen_id
from mascope_backend.socket.records import (
    emit_record_created,
    emit_record_deleted,
    emit_record_reload,
    emit_record_updated,
)


@api_controller()
async def get_datasets(
    workspace_id: str | None = None,
    dataset_name: str | None = None,
    dataset_type: list[str] | None = None,
    instrument: list[str] | None = None,
    sort: str = "dataset_utc_created",
    order: str = "asc",
    page: int | None = None,
    limit: int | None = None,
) -> dict:
    """
    Retrieves a paginated list of datasets, optionally sorted by a specified column in
    either ascending or descending order.

    Steps:
    1. Construct a SQLAlchemy query to select all datasets.
    2. Apply sorting if specified by the sort and order parameters.
    3. Apply pagination based on the page and limit parameters.
    4. Execute the query to fetch the results.
    5. Convert the results into a list of dictionaries for JSON serialization.

    :param workspace_id: Optional workspace ID to filter datasets by their associated
                         workspace.
    :type workspace_id: str | None, optional
    :param dataset_name: Filter datasets by name, defaults to None
    :type dataset_name: str | None, optional
    :param dataset_type: Filter datasets by type (ACQUISITION or ANALYSIS), defaults to
                         None
    :type dataset_type: list[str] | None, optional
    :param instrument: Filter datasets by instrument associated with the dataset,
                       defaults to None
    :type instrument: list[str] | None, optional
    :param sort: Column to sort by, defaults to "dataset_utc_created"
    :type sort: str, optional
    :param order: Sorting order ('asc' for ascending, 'desc' for descending),
                  defaults to "asc"
    :type order: str, optional
    :param page: Page number for pagination, defaults to None (no pagination).
    :type page: int | None, optional
    :param limit: Number of items per page, defaults to None (no pagination).
    :type limit: int | None, optional
    :return: A dictionary with the total count and a list of datasets.
    :rtype: dict
    """
    # Validate pagination parameters
    if (page is None) != (limit is None):
        raise ValueError(
            "Both 'page' and 'limit' must be provided together or both omitted."
        )
    async with async_session() as session:
        stmt = select(Dataset)

        # Filter by workspace if specified (routes always provide this;
        # internal/system callers may omit for cross-workspace queries)
        if workspace_id is not None:
            stmt = stmt.filter(Dataset.workspace_id == workspace_id)

        # Step 1: Filter by provided parameters
        if dataset_name:
            stmt = stmt.filter(Dataset.dataset_name == dataset_name)

        if dataset_type:
            stmt = stmt.filter(Dataset.dataset_type.in_(dataset_type))

        if instrument:
            stmt = stmt.filter(Dataset.instrument.in_(instrument))

        # Step 2: Apply sorting if specified
        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(Dataset, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(Dataset, sort)))

        # Step 3: Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt)

        # Step 4: Apply pagination
        if page is not None and limit is not None:
            stmt = stmt.offset(page * limit).limit(limit)

        # Step 5: Execute the query
        result = await session.execute(stmt)
        datasets = result.scalars().all()

    # Step 6: Return the total count and the list of validated datasets
    return {
        "message": "Datasets retrieved successfully",
        "results": total,
        "data": [
            DatasetRead.model_validate(dataset).model_dump() for dataset in datasets
        ],
    }


@api_controller()
async def get_dataset(dataset_id: str, workspace_id: str | None = None) -> dict:
    """
    Retrieves a single dataset by its unique ID.

    Steps:
    1. Execute a query to fetch the dataset with the specified ID.
    2. Check if the dataset exists. If not, raise a NotFoundException.
    3. Verify the dataset belongs to the specified workspace.
    4. Return the dataset's details as a dictionary.

    :param dataset_id: Unique identifier of the dataset to retrieve.
    :type dataset_id: str
    :param workspace_id: ID of the workspace the dataset must belong to.
    :type workspace_id: str
    :raises NotFoundException: If the dataset with the given ID is not found.
    :return: The requested dataset's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch dataset by ID
        dataset = await session.get(Dataset, dataset_id)

        if not dataset or (
            workspace_id is not None and dataset.workspace_id != workspace_id
        ):
            # Step 2: If dataset not found or wrong workspace, raise exception
            raise NotFoundException(f"Dataset with ID '{dataset_id}' not found")

    # Step 3: Return dataset details
    return {
        "message": f"Dataset '{dataset.dataset_name}' retrieved successfully",
        "data": DatasetRead.model_validate(dataset).model_dump(),
    }


@api_controller()
async def create_dataset(
    workspace_id: str,
    dataset: DatasetCreate,
    independent_transaction: bool = False,
) -> dict:
    """
    Creates a new dataset with the specified details.

    Steps:
    1. Create a new Dataset object with the provided details and the generated ID.
    2. Add the new dataset to the session and commit the changes to the database.
    3. Emit a signal to inform clients about the creation of the new dataset.
    4. Return the details of the created dataset.

    :param workspace_id: The ID of the workspace to which the dataset belongs.
    :type workspace_id: str
    :param dataset: Dataset creation details from the request body.
    :type dataset: DatasetCreate
    :param independent_transaction: Flag to indicate if the operation should be treated
                                    as an independent transaction, defaults to False.
    :type independent_transaction: bool, optional
    :return: The created dataset's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Generate unique ID and create new dataset
        new_dataset = Dataset(
            dataset_id=gen_id(16),
            workspace_id=workspace_id,
            **dataset.model_dump(),
            locked=(
                1
                if dataset.dataset_type == "ACQUISITION"
                and dataset_config.ACQUISITION_AUTO_LOCK
                else 0
            ),  # Auto-lock acquisition datasets
            dataset_utc_created=datetime.now(timezone.utc),
        )

        # Step 2: Add to session and commit
        session.add(new_dataset)
        await session.commit()
        await session.refresh(new_dataset)

    # Step 3: Emit creation event to all clients
    dataset_data = DatasetRead.model_validate(new_dataset).model_dump()
    if independent_transaction:
        await emit_record_created(
            record_type="dataset",
            record_id=new_dataset.dataset_id,
            record=dataset_data,
        )

    # Step 4: Return the new dataset details
    return {
        "message": f"Dataset '{new_dataset.dataset_name}' created successfully.",
        "data": dataset_data,
    }


@api_controller()
async def update_dataset(
    dataset_id: str,
    dataset_update: DatasetUpdate,
    workspace_id: str | None = None,
    independent_transaction: bool = False,
) -> dict:
    """
    Updates an existing dataset with new data provided in the dataset update request
    body.

    Steps:
    1. Fetch the existing dataset by its ID from the database.
    2. If the dataset is found, update its properties with the new data provided.
    3. Set the dataset's modification timestamp to the current UTC time.
    4. Commit the updated dataset to the database.
    5. Emit socket.io events to inform clients about the dataset update.

    :param dataset_id: The unique identifier of the dataset to update.
    :type dataset_id: str
    :param dataset_update: The new data for the dataset update.
    :type dataset_update: DatasetUpdate
    :param workspace_id: The workspace the dataset belongs to (optional, used for
                         validation).
    :type workspace_id: str | None, optional
    :param independent_transaction: Flag indicating if operation is independent
                                    transaction, defaults to False.
    :type independent_transaction: bool, optional
    :raises NotFoundException: If no dataset is found with the provided ID.
    :return: The updated dataset data as a dictionary.
    :rtype: dict
    """
    # Step 1: Fetch the existing dataset
    async with async_session() as session:
        update_data = dataset_update.model_dump(exclude_unset=True)
        existing_dataset = await session.get(Dataset, dataset_id)
        if not existing_dataset or (
            workspace_id is not None and existing_dataset.workspace_id != workspace_id
        ):
            raise NotFoundException(f"Dataset with ID '{dataset_id}' not found")

        # Step 2: Validate ACQUISITION dataset constraints
        if (
            existing_dataset.dataset_type == "ACQUISITION"
            and "dataset_name" in update_data
        ):
            new_name = update_data.get("dataset_name", None)
            instrument = existing_dataset.instrument

            if instrument is None:
                raise ValueError(
                    "Acquisition dataset must have an associated instrument."
                )

            if new_name and not new_name.lower().endswith(instrument.lower()):
                raise ValueError(
                    f"Acquisition dataset name should end with the instrument name. "
                    "Suggested: "
                    f"{dataset_config.ACQUISITION_NAME_PREFIX} {instrument}"
                )

        # Step 3: Update the dataset properties
        for key, value in update_data.items():
            setattr(existing_dataset, key, value)

        # Step 4: Update modification timestamp
        existing_dataset.dataset_utc_modified = datetime.now(timezone.utc)

        # Step 5: Commit the updates
        await session.commit()
        await session.refresh(existing_dataset)

    # Step 6: Emit update event to all clients
    dataset_data = DatasetRead.model_validate(existing_dataset).model_dump()
    if independent_transaction:
        await emit_record_updated(
            record_type="dataset",
            record_id=dataset_id,
            record=dataset_data,
        )

    return {
        "message": f"Dataset '{existing_dataset.dataset_name}' updated successfully.",
        "data": dataset_data,
    }


@api_controller()
async def delete_dataset(
    dataset_id: str,
    workspace_id: str | None = None,
    independent_transaction: bool = False,
) -> dict:
    """
    Deletes a dataset by its unique identifier.

    Steps:
    1. Fetch the dataset by its ID from the database.
    2. If the dataset is found, delete it from the session and commit the changes to
       the database.
    3. Emit socket.io events to inform clients about the dataset deletion.

    :param dataset_id: The unique identifier of the dataset to delete.
    :type dataset_id: str
    :param independent_transaction: Flag indicating if operation is independent
                                    transaction, defaults to False.
    :type independent_transaction: bool, optional
    :raises NotFoundException: If no dataset is found with the provided ID.
    """
    # Step 1: Fetch the dataset
    async with async_session() as session:
        dataset = await session.get(Dataset, dataset_id)
        if not dataset or (
            workspace_id is not None and dataset.workspace_id != workspace_id
        ):
            raise NotFoundException(f"Dataset with ID '{dataset_id}' not found")

        # Step 2: Delete the dataset and commit changes
        await session.delete(dataset)
        await session.commit()

    # Step 3: Emit deletion event to all clients
    dataset_name = dataset.dataset_name
    if independent_transaction:
        await emit_record_deleted(
            record_type="dataset",
            record_id=dataset_id,
        )

    return {
        "message": f"Dataset '{dataset_name}' deleted successfully.",
    }


@api_controller()
async def move_dataset(
    dataset_id: str,
    target_workspace_id: str,
    independent_transaction: bool = False,
) -> dict:
    """
    Move a dataset into another workspace by reassigning its workspace_id.

    No child rows are modified: batches and samples reference the dataset, and
    workspace ACL resolves dataset -> workspace at query time, so the entire
    subtree's access flips on this single foreign-key write.

    Steps:
    - Fetch the dataset by ID.
    - Reject ACQUISITION datasets, which are auto-managed across workspaces.
    - Reject a no-op move where the target equals the current workspace.
    - Validate the target workspace exists, is non-system and active.
    - Reassign workspace_id, bump the modified timestamp and commit.
    - Broadcast a dataset reload so clients re-fetch their workspace list.

    :param dataset_id: The unique identifier of the dataset to move.
    :type dataset_id: str
    :param target_workspace_id: The workspace to move the dataset into.
    :type target_workspace_id: str
    :param independent_transaction: Emit a socket reload when standalone,
                                    defaults to False.
    :type independent_transaction: bool, optional
    :raises NotFoundException: If no dataset is found with the provided ID.
    :raises WorkspaceNotFoundException: If the target workspace does not exist.
    :raises HTTPException: 400 for ACQUISITION datasets, no-op moves, or an
                           inactive target; 403 for a system target.
    :return: The moved dataset's details.
    :rtype: dict
    """
    async with async_session() as session:
        # --- Fetch the dataset ---
        dataset = await session.get(Dataset, dataset_id)
        if not dataset:
            raise NotFoundException(f"Dataset with ID '{dataset_id}' not found")

        # --- Acquisition datasets are auto-managed - never relocate ---
        if dataset.dataset_type == "ACQUISITION":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Acquisition datasets cannot be moved between workspaces.",
            )

        # --- Reject no-op move explicitly (client error, not silent pass) ---
        if target_workspace_id == dataset.workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dataset is already in the target workspace.",
            )

        # --- Validate the target workspace exists and is active/non-system ---
        target = await session.get(Workspace, target_workspace_id)
        if target is None:
            raise WorkspaceNotFoundException(target_workspace_id)
        if target.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot move datasets into a system workspace.",
            )
        if target.workspace_status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot move datasets into an archived workspace.",
            )

        # --- Reassign workspace and bump modification timestamp ---
        dataset.workspace_id = target_workspace_id
        dataset.dataset_utc_modified = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(dataset)

    # --- Reload so both source and target workspace lists re-fetch updated data ---
    dataset_data = DatasetRead.model_validate(dataset).model_dump()
    if independent_transaction:
        await emit_record_reload(record_type="dataset")

    return {
        "message": f"Dataset '{dataset.dataset_name}' moved successfully.",
        "data": dataset_data,
    }
