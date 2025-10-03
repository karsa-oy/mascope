from fastapi import APIRouter, Depends
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.match.targets.batch.match_targets_batch_controller import (
    get_batch_data,
)
from mascope_backend.api.new.auth.dependencies import guest_user

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

    TODO refactor - move this to a better resource, after creating `match/records` resource

    This function is used in the `mascope_sdk` library, serving as a wrapper for Jupyter
    notebooks, enabling easy retrieval of batch match data in batch selector widgets.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: Batch data including samples, compounds, ions, and isotopes.
    :rtype: dict
    """
    return await get_batch_data(sample_batch_id=sample_batch_id)
