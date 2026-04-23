"""
Dataset management routes.

This module provides endpoints for dataset operations including
CRUD operations and dataset management functionality.
"""

from fastapi import APIRouter, Depends, Query

from mascope_backend.api.controllers.dataset.dataset_controller import (
    create_dataset,
    delete_dataset,
    get_dataset,
    get_datasets,
    update_dataset,
)
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.models.dataset.dataset_pydantic_model import (
    GetDatasetsQueryParams,
    DatasetCreate,
    DatasetUpdate,
)
from mascope_backend.api.new.auth.access_rules import locked_access
from mascope_backend.api.new.auth.dependencies import (
    editor_user,
    guest_user,
)
from mascope_backend.api.routes.dataset.acquisition.routes import (
    acquisition_datasets_router,
)
from mascope_backend.db import Dataset


dataset_router = APIRouter(prefix="/api/datasets", tags=["Dataset"])
dataset_router.include_router(acquisition_datasets_router)


@dataset_router.get("")
@api_route(token_access=True)
async def get_datasets_route(
    query_params: GetDatasetsQueryParams = Query(),
    user=Depends(guest_user),
):
    """Retrieve a list of datasets.

    :param query_params: Query parameters for sorting and pagination, defaults to Depends().
    :type query_params: GetDatasetsQueryParams, optional
    :param user: The current authenticated user, defaults to Depends(guest_user).
    :type user: User, optional
    :return: A dictionary containing total count and list of datasets.
    :rtype: dict
    """
    return await get_datasets(**query_params.model_dump())


@dataset_router.get("/{dataset_id}")
@api_route()
async def get_dataset_route(dataset_id: str, user=Depends(guest_user)):
    """Retrieve details of a specific dataset by ID.

    :param dataset_id: The unique identifier of the dataset.
    :type dataset_id: str
    :param user: The current authenticated user, defaults to Depends(guest_user).
    :type user: User, optional
    :return: A dictionary containing the dataset details.
    :rtype: dict
    """
    return await get_dataset(dataset_id)


@dataset_router.patch("/{dataset_id}")
@api_route()
async def update_dataset_route(
    dataset_id: str, dataset_update: DatasetUpdate, user=Depends(editor_user)
):
    """Update an existing dataset's details.

    Locked datasets can only be updated by owners.

    :param dataset_id: The unique identifier of the dataset.
    :type dataset_id: str
    :param dataset_update: The dataset update data.
    :type dataset_update: DatasetUpdate
    :param user: The current authenticated user with editor permissions, defaults to Depends(editor_user).
    :type user: User, optional
    :return: A dictionary containing the updated dataset details.
    :rtype: dict
    """
    # Check if locked dataset - only owners can update
    await locked_access(user, Dataset, dataset_id, min_role="owner")
    return await update_dataset(
        dataset_id=dataset_id,
        dataset_update=dataset_update,
        independent_transaction=True,
    )


@dataset_router.post("")
@api_route(status_code=201)
async def create_dataset_route(dataset: DatasetCreate, user=Depends(editor_user)):
    """Create a new dataset.

    :param dataset: The dataset creation data.
    :type dataset: DatasetCreate
    :param user: The current authenticated user with editor permissions, defaults to Depends(editor_user).
    :type user: User, optional
    :return: A dictionary containing the newly created dataset's details.
    :rtype: dict
    """
    return await create_dataset(dataset=dataset, independent_transaction=True)


@dataset_router.delete("/{dataset_id}")
@api_route()
async def delete_dataset_route(dataset_id: str, user=Depends(editor_user)):
    """Delete a specific dataset by ID.

    Locked datasets can only be deleted by owners.

    :param dataset_id: The unique identifier of the dataset.
    :type dataset_id: str
    :param user: The current authenticated user with editor permissions, defaults to Depends(editor_user).
    :type user: User, optional
    :return: A dictionary confirming deletion (if applicable).
    :rtype: dict or None
    """
    # Check if locked dataset - only owners can delete
    await locked_access(user, Dataset, dataset_id, min_role="owner")
    return await delete_dataset(
        dataset_id=dataset_id, independent_transaction=True
    )
