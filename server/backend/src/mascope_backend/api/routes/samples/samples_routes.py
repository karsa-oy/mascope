from fastapi import APIRouter, Depends, Query
from mascope_backend.api.new.auth.dependencies import guest_user
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.samples.samples_controller import (
    get_samples,
    get_sample,
    get_sample_peaks,
    get_sample_peak_timeseries,
    get_sample_spectrum,
    get_samples_spectra,
)
from mascope_backend.api.models.samples.sample_pydantic_model import (
    GetSamplePeakTimeseriesBody,
    GetSamplePeaksQueryParams,
    GetSamplesQueryParams,
    GetSampleSpectrumQueryParams,
)

samples_router = APIRouter(prefix="/api/samples", tags=["Samples Loading"])


@samples_router.get("")
@api_route(token_access=True)
async def get_samples_route(
    query_params: GetSamplesQueryParams = Query(), user=Depends(guest_user)
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


@samples_router.get("/{sample_item_id}/peaks")
@api_route(token_access=True)
async def get_sample_peaks_route(
    sample_item_id: str,
    query_params: GetSamplePeaksQueryParams = Depends(),
    user=Depends(guest_user),
):
    """
    Retrieve peak data from a sample with automatic polarity filtering and optional range filtering.

    This endpoint extracts peak areas and/or heights for a sample, automatically filtered by the sample's
    polarity so that only scans matching the sample's polarity are included. Supports optional time
    range filtering within the sample's acquisition window (t0/t1) and m/z range filtering.
    The peak data is aggregated across the time dimension (averaged or summed) after applying all filters.

    :param sample_item_id: The unique identifier of the sample
    :param query_params: Query parameters for peak filtering including time range and data selection
    :param user: Authenticated user with guest access
    :return: Peak data filtered by sample's polarity and time range
    """
    return await get_sample_peaks(
        sample_item_id=sample_item_id, **query_params.model_dump()
    )


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


@samples_router.get("/{sample_item_id}/spectrum")
@api_route(token_access=True)
async def get_sample_spectrum_route(
    sample_item_id: str,
    query_params: GetSampleSpectrumQueryParams = Depends(),
    user=Depends(guest_user),
):
    """
    Retrieve spectrum data from a sample with automatic polarity filtering and optional range filtering.

    This endpoint extracts time-averaged spectrum data for a sample, automatically filtered by the sample's
    polarity. Supports optional time range filtering (t_min/t_max) within the sample's acquisition window (t0/t1)
    and m/z range filtering.

    :param sample_item_id: The unique identifier of the sample
    :param query_params: Query parameters for spectrum filtering including optional time and m/z ranges
    :param user: Authenticated user with guest access
    :return: Spectrum data with m/z values and intensities, filtered by sample polarity
    """
    return await get_sample_spectrum(
        sample_item_id=sample_item_id, **query_params.model_dump()
    )


@samples_router.get("/{sample_item_ids}/spectra")
@api_route(token_access=True)
async def get_samples_spectra_route(
    sample_item_ids: str,
    query_params: GetSampleSpectrumQueryParams = Depends(),
    user=Depends(guest_user),
):
    """
    Retrieve spectrum data for multiple samples with automatic polarity filtering and optional range filtering.

    This endpoint extracts time-averaged spectrum data for multiple samples, automatically filtered by each sample's
    polarity. Supports optional time range filtering (t_min/t_max) within each sample's acquisition window (t0/t1)
    and m/z range filtering.

    :param sample_item_ids: Comma-separated list of sample item IDs to retrieve spectra for
    :param query_params: Query parameters for spectrum filtering including optional time and m/z ranges
    :param user: Authenticated user with guest access
    :return: Spectrum data with m/z values and intensities, filtered by sample polarity
    """
    sample_item_ids = sample_item_ids.split(",")

    return await get_samples_spectra(
        sample_item_ids=sample_item_ids, **query_params.model_dump()
    )
