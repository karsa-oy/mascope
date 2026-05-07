"""
Acquisition dataset management routes.

This module provides endpoints for automatic creation and cleanup
of acquisition datasets based on available instruments.
"""

from fastapi import APIRouter, Depends, Query

from mascope_backend.api.controllers.dataset.acquisition.service import (
    create_acquisition_datasets,
    delete_acquisition_datasets,
    get_acquisition_dataset,
)
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.models.dataset.acquisition.schemas import (
    GetAcquisitionDatasetQueryParams,
)
from mascope_backend.api.new.auth.dependencies import guest_user, owner_user


acquisition_datasets_router = APIRouter(
    prefix="/api/datasets/acquisition", tags=["Acquisition Dataset Management"]
)


@acquisition_datasets_router.get("")
@api_route(token_access=True)
async def get_acquisition_dataset_route(
    query_params: GetAcquisitionDatasetQueryParams = Query(),
    user=Depends(guest_user),
):
    """Retrieve a list of datasets.

    :param query_params: Query parameters for sorting and pagination, defaults to
                         Depends().
    :type query_params: GetDatasetsQueryParams, optional
    :param user: The current authenticated user, defaults to Depends(guest_user).
    :type user: User, optional
    :return: A dictionary containing total count and list of datasets.
    :rtype: dict
    """
    return await get_acquisition_dataset(**query_params.model_dump())


@acquisition_datasets_router.post("")
@api_route(status_code=201)
async def create_acquisition_datasets_route(user=Depends(owner_user)):
    """Auto-create missing acquisition datasets for all instruments.

    Creates acquisition datasets for instruments that don't have them yet.
    This endpoint is primarily used for:
    - System initialization and setup
    - Testing and development
    - Manual dataset creation when automatic creation fails

    :param user: The current authenticated user with owner permissions.
    :type user: User
    :return: A dictionary containing the summary of created datasets.
    :rtype: dict
    :raises ForbiddenAccessException: If user doesn't have owner permissions.
    """
    return await create_acquisition_datasets()


@acquisition_datasets_router.delete("")
@api_route()
async def delete_acquisition_datasets_route(user=Depends(owner_user)):
    """Auto-delete orphaned acquisition datasets for instruments that no longer exist.

    Removes acquisition datasets for instruments that have no sample files.
    This endpoint is useful for:
    - System cleanup and maintenance
    - Testing and development
    - Data consistency checks

    Safety Notes:
    - Only deletes datasets for instruments with zero sample files
    - Does not affect datasets with valid existing instruments
    - Cannot accidentally delete datasets with data

    :param user: The current authenticated user with owner permissions.
    :type user: User
    :return: A dictionary containing the summary of deleted datasets.
    :rtype: dict
    :raises ForbiddenAccessException: If user doesn't have owner permissions.
    """
    return await delete_acquisition_datasets()
