from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.match.targets.batch.match_targets_batch_controller import (
    get_batch_data,
    get_match_batch_collections,
    get_match_batch_compounds,
    get_match_batch_ions,
    get_match_batch_isotopes,
)
from mascope_server.api.models.match.targets.batch.match_targets_batch_pydantic_model import (
    SortingPaginationQueryParams,
    GetMatchBatchCompoundsQueryParams,
    GetMatchBatchIonsQueryParams,
    GetMatchBatchIsotopesQueryParams,
)
from mascope_server.api.new.auth.dependencies import guest_user

match_targets_batch_router = APIRouter(
    prefix="/api/match/targets/batch", tags=["Match Batch Loading"]
)


@match_targets_batch_router.get("/{sample_batch_id}")
@api_route(token_access=True)
async def get_batch_data_route(
    sample_batch_id: str,
    user=Depends(guest_user),
):
    """Retrieve detailed match data for a specific sample batch.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: Batch data including samples, compounds, ions, and isotopes.
    :rtype: dict
    """
    return await get_batch_data(sample_batch_id=sample_batch_id)


@match_targets_batch_router.get("/{sample_batch_id}/collections")
@api_route()
async def get_match_batch_collections_route(
    sample_batch_id: str,
    query_params: SortingPaginationQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve target collection matches for a specific sample batch.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param query_params: Sorting and pagination parameters.
    :type query_params: SortingPaginationQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary with matched collections data.
    :rtype: dict
    """
    return await get_match_batch_collections(
        sample_batch_id=sample_batch_id, **query_params.model_dump()
    )


@match_targets_batch_router.get("/{sample_batch_id}/compounds")
@api_route()
async def get_match_batch_compounds_route(
    sample_batch_id: str,
    query_params: GetMatchBatchCompoundsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve matched compounds for a specific sample batch.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param query_params: Query parameters for compound filtering and pagination.
    :type query_params: GetMatchBatchCompoundsQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary with matched compounds data.
    :rtype: dict
    """
    return await get_match_batch_compounds(
        sample_batch_id=sample_batch_id, **query_params.model_dump()
    )


@match_targets_batch_router.get("/{sample_batch_id}/ions")
@api_route()
async def get_match_batch_ions_route(
    sample_batch_id: str,
    query_params: GetMatchBatchIonsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve matched ions for a specific sample batch.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param query_params: Query parameters for ion filtering and pagination.
    :type query_params: GetMatchBatchIonsQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary with matched ions data.
    :rtype: dict
    """
    return await get_match_batch_ions(
        sample_batch_id=sample_batch_id, **query_params.model_dump()
    )


@match_targets_batch_router.get("/{sample_batch_id}/isotopes")
@api_route()
async def get_match_batch_isotopes_route(
    sample_batch_id: str,
    query_params: GetMatchBatchIsotopesQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve matched isotopes for a specific sample batch.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param query_params: Query parameters for isotope filtering and pagination.
    :type query_params: GetMatchBatchIsotopesQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary with matched isotopes data.
    :rtype: dict
    """
    return await get_match_batch_isotopes(
        sample_batch_id=sample_batch_id, **query_params.model_dump()
    )
