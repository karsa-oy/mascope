from fastapi import APIRouter, Depends

from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.new.auth.dependencies import guest_user

from .schema import (
    GetMs1CentroidsQueryParams,
    GetMs2CentroidsQueryParams,
    GetMs2SummaryQueryParams,
    GetMs2TimeseriesQueryParams,
)
from .service import (
    get_ms1_averaged_centroids,
    get_ms2_averaged_centroids,
    get_ms2_summary,
    get_ms2_timeseries,
)


ms2_router = APIRouter(tags=["MS2 Analysis"])


@ms2_router.get("/{sample_item_id}/ms2/summary")
@api_route(token_access=True)
async def get_ms2_summary_route(
    sample_item_id: str,
    query_params: GetMs2SummaryQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve MS2 summary (parent peaks, HCD map, isolation width).

    :param sample_item_id: The unique identifier of the sample.
    :param query_params: Query parameters for MS2 summary including parent peak tolerance.
    :param user: Authenticated user with guest access.
    :return: MS2 summary data.
    """
    return await get_ms2_summary(
        sample_item_id=sample_item_id,
        **query_params.model_dump(),
    )


@ms2_router.get("/{sample_item_id}/ms2/ms1_centroids")
@api_route(token_access=True)
async def get_ms1_averaged_centroids_route(
    sample_item_id: str,
    query_params: GetMs1CentroidsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve averaged MS1 centroids for a sample.

    :param sample_item_id: The unique identifier of the sample.
    :param query_params: Query parameters for MS1 centroid retrieval.
    :param user: Authenticated user with guest access.
    :return: Averaged MS1 centroid data.
    """
    return await get_ms1_averaged_centroids(
        sample_item_id=sample_item_id,
        **query_params.model_dump(),
    )


@ms2_router.get("/{sample_item_id}/ms2/centroids")
@api_route(token_access=True)
async def get_ms2_averaged_centroids_route(
    sample_item_id: str,
    query_params: GetMs2CentroidsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve averaged MS2 centroids for each parent peak.

    :param sample_item_id: The unique identifier of the sample.
    :param query_params: Query parameters for MS2 centroid retrieval.
    :param user: Authenticated user with guest access.
    :return: Averaged MS2 centroids per parent peak.
    """
    return await get_ms2_averaged_centroids(
        sample_item_id=sample_item_id,
        **query_params.model_dump(),
    )


@ms2_router.get("/{sample_item_id}/ms2/timeseries")
@api_route(token_access=True)
async def get_ms2_timeseries_route(
    sample_item_id: str,
    query_params: GetMs2TimeseriesQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve fragment timeseries for a single parent peak.

    :param sample_item_id: The unique identifier of the sample.
    :param query_params: Query parameters for MS2 timeseries retrieval.
    :param user: Authenticated user with guest access.
    :return: Fragment timeseries data.
    """
    return await get_ms2_timeseries(
        sample_item_id=sample_item_id,
        **query_params.model_dump(),
    )
