from typing import Literal

from fastapi import APIRouter, Depends, Query

from mascope_backend.api.controllers.samples.ms2 import (
    get_ms1_averaged_centroids,
    get_ms2_averaged_centroids,
    get_ms2_summary,
    get_ms2_timeseries,
)
from mascope_backend.api.controllers.samples.samples_controller import (
    get_sample,
    get_sample_peak_timeseries,
    get_sample_peaks,
    get_sample_spectrum,
    get_samples,
    get_samples_centroids,
    get_samples_spectra,
)
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.models.samples.sample_pydantic_model import (
    GetSamplePeaksQueryParams,
    GetSamplePeakTimeseriesBody,
    GetSampleSpectrumQueryParams,
    GetSamplesQueryParams,
)
from mascope_backend.api.new.auth.dependencies import guest_user


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


@samples_router.get("/centroids")
@api_route(token_access=True)
async def get_samples_centroids_route(
    sample_item_ids: list[str] = Query(..., description="List of sample item IDs"),
    user=Depends(guest_user),
) -> dict:
    """Retrieve centroids for multiple sample items.

    :param sample_item_ids: List of sample item IDs to retrieve centroids for.
    :param user: The current authenticated user with editor permissions.
    :return: A dictionary containing the process ID for retrieving centroids.
    """
    return await get_samples_centroids(sample_item_ids=sample_item_ids)


@samples_router.get("/spectra")
@api_route(token_access=True)
async def get_samples_spectra_route(
    sample_item_ids: list[str] = Query(..., description="List of sample item IDs"),
    t_min: float | None = Query(None),
    t_max: float | None = Query(None),
    mz_min: float | None = Query(None),
    mz_max: float | None = Query(None),
    user=Depends(guest_user),
):
    """Retrieve spectra for multiple samples with optional filtering.

    :param sample_item_ids: List of sample item IDs to retrieve spectra for.
    :type sample_item_ids: list[str], optional
    :param t_min: Minimum time value for filtering spectra, defaults to Query(None)
    :type t_min: float | None, optional
    :param t_max: Maximum time value for filtering spectra, defaults to Query(None)
    :type t_max: float | None, optional
    :param mz_min: Minimum m/z value for filtering spectra, defaults to Query(None)
    :type mz_min: float | None, optional
    :param mz_max: Maximum m/z value for filtering spectra, defaults to Query(None)
    :type mz_max: float | None, optional
    :param user: The current authenticated user with guest permissions.
    :type user: optional
    :return: A dictionary containing the spectra for the specified samples.
    :rtype: dict
    """
    return await get_samples_spectra(
        sample_item_ids=sample_item_ids,
        t_min=t_min,
        t_max=t_max,
        mz_min=mz_min,
        mz_max=mz_max,
    )


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


# ──────────────────────────────────────────────────────────────────────────────
# MS2 Analysis routes
# ──────────────────────────────────────────────────────────────────────────────


@samples_router.get("/{sample_item_id}/ms2/summary")
@api_route(token_access=True)
async def get_ms2_summary_route(
    sample_item_id: str,
    parent_peak_tolerance: float = Query(
        0.001, description="Tolerance in Da for merging parent peaks"
    ),
    user=Depends(guest_user),
):
    """Retrieve MS2 summary (parent peaks, HCD map, isolation width).

    :param sample_item_id: The unique identifier of the sample.
    :param parent_peak_tolerance: Tolerance for merging near-duplicate parent peaks.
    :param user: Authenticated user with guest access.
    :return: MS2 summary data.
    """
    return await get_ms2_summary(
        sample_item_id=sample_item_id,
        parent_peak_tolerance=parent_peak_tolerance,
    )


@samples_router.get("/{sample_item_id}/ms2/ms1_centroids")
@api_route(token_access=True)
async def get_ms1_averaged_centroids_route(
    sample_item_id: str,
    ppm: int = Query(1, description="Mass tolerance in ppm for centroid binning"),
    user=Depends(guest_user),
):
    """Retrieve averaged MS1 centroids for a sample.

    :param sample_item_id: The unique identifier of the sample.
    :param ppm: Mass tolerance in ppm for centroid binning.
    :param user: Authenticated user with guest access.
    :return: Averaged MS1 centroid data.
    """
    return await get_ms1_averaged_centroids(
        sample_item_id=sample_item_id,
        ppm=ppm,
    )


@samples_router.get("/{sample_item_id}/ms2/centroids")
@api_route(token_access=True)
async def get_ms2_averaged_centroids_route(
    sample_item_id: str,
    noise_threshold: float = Query(
        10.0, description="Minimum signal-to-noise ratio threshold"
    ),
    parent_peak_tolerance: float = Query(
        0.001, description="Tolerance in Da for merging parent peaks"
    ),
    user=Depends(guest_user),
):
    """Retrieve averaged MS2 centroids for each parent peak.

    :param sample_item_id: The unique identifier of the sample.
    :param noise_threshold: Minimum SNR for peak inclusion.
    :param parent_peak_tolerance: Tolerance for merging near-duplicate parent peaks.
    :param user: Authenticated user with guest access.
    :return: Averaged MS2 centroids per parent peak.
    """
    return await get_ms2_averaged_centroids(
        sample_item_id=sample_item_id,
        noise_threshold=noise_threshold,
        parent_peak_tolerance=parent_peak_tolerance,
    )


@samples_router.get("/{sample_item_id}/ms2/timeseries")
@api_route(token_access=True)
async def get_ms2_timeseries_route(
    sample_item_id: str,
    parent_peak_mz: float = Query(
        ..., description="Parent peak m/z to get fragment timeseries for"
    ),
    noise_threshold: float = Query(
        10.0, description="Minimum signal-to-noise ratio threshold"
    ),
    parent_peak_tolerance: float = Query(
        0.001, description="Tolerance in Da for matching parent peaks"
    ),
    normalize_by: Literal["tic"] | None = Query(
        None, description="Normalization mode: 'tic' or None"
    ),
    user=Depends(guest_user),
):
    """Retrieve fragment timeseries for a single parent peak.

    :param sample_item_id: The unique identifier of the sample.
    :param parent_peak_mz: Target parent peak m/z value.
    :param noise_threshold: Minimum SNR for peak inclusion.
    :param parent_peak_tolerance: Tolerance for matching parent peaks.
    :param normalize_by: Normalization mode: 'tic' or None.
    :param user: Authenticated user with guest access.
    :return: Fragment timeseries data.
    """
    return await get_ms2_timeseries(
        sample_item_id=sample_item_id,
        parent_peak_mz=parent_peak_mz,
        noise_threshold=noise_threshold,
        parent_peak_tolerance=parent_peak_tolerance,
        normalize_by=normalize_by,
    )
