from fastapi import APIRouter, Depends
from mascope_backend.api.new.auth.dependencies import guest_user
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.samples.samples_controller import (
    get_samples,
    get_sample,
    get_sample_peak_timeseries,
)
from mascope_backend.api.models.samples.sample_pydantic_model import (
    GetSamplePeakTimeseriesBody,
    GetSamplesQueryParams,
)

samples_router = APIRouter(prefix="/api/samples", tags=["Samples Loading"])


@samples_router.get("")
@api_route(token_access=True)
async def get_samples_route(
    query_params: GetSamplesQueryParams = Depends(), user=Depends(guest_user)
):
    """Retrieve a list of samples based on query filters.

    :param query_params: Query parameters for filtering, sorting, and pagination.
    :param user: The current authenticated user with guest permissions.
    :return: A dictionary containing the total count and list of samples.
    """
    return await get_samples(**query_params.model_dump())


@samples_router.get("/{sample_item_id}")
@api_route(token_access=True)
async def get_sample_route(sample_item_id: str, user=Depends(guest_user)):
    """Retrieve details of a specific sample by ID.

    :param sample_item_id: The unique identifier of the sample.
    :param user: The current authenticated user with guest permissions.
    :return: A dictionary containing the sample details.
    """
    return await get_sample(sample_item_id=sample_item_id)


@samples_router.post("/{sample_item_id}/peaks/timeseries")
@api_route(token_access=True)
async def get_sample_peak_timeseries_route(
    sample_item_id: str, body: GetSamplePeakTimeseriesBody, user=Depends(guest_user)
):
    """
    Retrieve timeseries data for a specific peak in a sample.

    This endpoint extracts timeseries data for the closest peak to a given m/z value
    within the specified tolerance, filtered by the sample's polarity and time range.

    :param sample_item_id: The unique identifier of the sample
    :param body: Request body containing peak m/z, tolerance, and optional time filters
    :param user: Authenticated user with guest access
    :return: Timeseries data for the specified peak including m/z, height, and time coordinates
    """
    return await get_sample_peak_timeseries(
        sample_item_id=sample_item_id, **body.model_dump()
    )
