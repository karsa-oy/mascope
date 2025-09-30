from fastapi import APIRouter, Depends, Query
from mascope_backend.api.new.auth.dependencies import guest_user
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.match.targets.sample.match_targets_sample_controller import (
    get_match_sample_collections,
    get_match_sample_compounds,
    get_match_sample_ions,
    get_match_sample_isotopes,
)
from mascope_backend.api.models.match.targets.sample.match_targets_sample_pydantic_model import (
    SortingPaginationQueryParams,
    GetMatchSampleCompoundsQueryParams,
    GetMatchSampleIonsQueryParams,
    GetMatchSampleIsotopesQueryParams,
)

match_targets_sample_router = APIRouter(
    prefix="/api/match/targets/sample", tags=["Match Sample Loading"]
)


@match_targets_sample_router.get("/{sample_item_id}/collections")
@api_route()
async def get_match_sample_collections_route(
    sample_item_id: str,
    query_params: SortingPaginationQueryParams = Query(),
    user=Depends(guest_user),
):
    """Retrieve target collection matches for a specific sample item.

    :param sample_item_id: The unique identifier of the sample item.
    :type sample_item_id: str
    :param query_params: Sorting and pagination parameters.
    :type query_params: SortingPaginationQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary with matched collections data.
    :rtype: dict
    """
    return await get_match_sample_collections(
        sample_item_id=sample_item_id, **query_params.model_dump()
    )


@match_targets_sample_router.get("/{sample_item_id}/compounds")
@api_route()
async def get_match_sample_compounds_route(
    sample_item_id: str,
    query_params: GetMatchSampleCompoundsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve matched compounds for a specific sample item.

    :param sample_item_id: The unique identifier of the sample item.
    :type sample_item_id: str
    :param query_params: Query parameters for compound filtering and pagination.
    :type query_params: GetMatchSampleCompoundsQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary with matched compounds data.
    :rtype: dict
    """
    return await get_match_sample_compounds(
        sample_item_id=sample_item_id, **query_params.model_dump()
    )


@match_targets_sample_router.get("/{sample_item_id}/ions")
@api_route()
async def get_match_sample_ions_route(
    sample_item_id: str,
    query_params: GetMatchSampleIonsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve matched ions for a specific sample item.

    :param sample_item_id: The unique identifier of the sample item.
    :type sample_item_id: str
    :param query_params: Query parameters for ion filtering and pagination.
    :type query_params: GetMatchSampleIonsQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary with matched ions data.
    :rtype: dict
    """
    return await get_match_sample_ions(
        sample_item_id=sample_item_id, **query_params.model_dump()
    )


@match_targets_sample_router.get("/{sample_item_id}/isotopes")
@api_route()
async def get_match_sample_isotopes_route(
    sample_item_id: str,
    query_params: GetMatchSampleIsotopesQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve matched isotopes for a specific sample item.

    :param sample_item_id: The unique identifier of the sample item.
    :type sample_item_id: str
    :param query_params: Query parameters for isotope filtering and pagination.
    :type query_params: GetMatchSampleIsotopesQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary with matched isotopes data.
    :rtype: dict
    """
    return await get_match_sample_isotopes(
        sample_item_id=sample_item_id, **query_params.model_dump()
    )
