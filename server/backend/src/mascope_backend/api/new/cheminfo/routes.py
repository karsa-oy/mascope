from fastapi import APIRouter, Depends, BackgroundTasks
from mascope_backend.api.new.auth.dependencies import guest_user
from mascope_backend.api.lib.api_features import api_route

from mascope_backend.api.new.cheminfo.service import (
    retrieve_cheminfo_by_mz,
    match_cheminfo_by_mz,
)
from mascope_backend.api.new.cheminfo.schema import (
    CheminfoQueryBody,
    CheminfoMatchedQueryBody,
)
from mascope_backend.db.id import gen_id


cheminfo_router = APIRouter(prefix="/api/cheminfo", tags=["cheminfo"])


@cheminfo_router.post("/mz/query")
@api_route(token_access=True)
async def retrieve_cheminfo_by_mz_route(
    body: CheminfoQueryBody, user=Depends(guest_user)
) -> dict:
    """
    Query the ChemInfo database for molecular formulas matching a given m/z value.

    This endpoint queries the external ChemInfo API to find potential molecular formulas
    that match the provided m/z value within the specified precision. Results can be
    filtered by formula ranges and ionization mechanisms.

    :param body: Query parameters including m/z value, precision, formula ranges, and ionization mechanisms
    :type body: CheminfoQueryBody
    :return: List of potential molecular formulas matching the m/z value
    :rtype: dict
    """
    return await retrieve_cheminfo_by_mz(**body.model_dump())


@cheminfo_router.post("/mz/match/sample/{sample_item_id}")
@api_route(status_code=202)
async def match_cheminfo_mz_route(
    sample_item_id: str,
    body: CheminfoMatchedQueryBody,
    background_tasks: BackgroundTasks,
    user=Depends(guest_user),
) -> dict:
    """
    Query the ChemInfo database by m/z and other optional parameters.

    This endpoint first queries the ChemInfo database for potential molecular formulas
    matching the given m/z, then matches these formulas against a specific sample.

    :param body: request query options; the only required field is `mz`
    :type body: CheminfoQueryBody
    :rtype dict:
    """
    # Get the socket ID from request headers for notifications
    process_id = gen_id(8)

    # Add background task for processing
    background_tasks.add_task(
        match_cheminfo_by_mz,
        sample_item_id=sample_item_id,
        mz=body.mz,
        mz_precision=body.mz_precision,
        formula_ranges=body.formula_ranges,
        ionization_mechanism_ids=body.ionization_mechanism_ids,
        match_params=body.match_params,
        sort=body.sort,
        order=body.order,
        independent_transaction=True,
        user_id=user.id,
        process_id=process_id,
    )

    return {
        "message": f"Matching potential molecular formulas for m/z {body.mz}, please wait.",
        "process_id": process_id,
    }
