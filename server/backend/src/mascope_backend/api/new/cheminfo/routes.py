from fastapi import APIRouter, Depends
from mascope_backend.api.new.auth.dependencies import guest_user
from mascope_backend.api.lib.api_features import api_route

from mascope_backend.api.new.cheminfo.service import (
    cheminfo_by_mz,
    cheminfo_by_mz_matched,
)
from mascope_backend.api.new.cheminfo.schema import (
    CheminfoQueryBody,
    CheminfoMatchedQueryBody,
)


cheminfo_router = APIRouter(prefix="/api/cheminfo", tags=["cheminfo"])


@cheminfo_router.post("/mz/query")
@api_route()
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


@cheminfo_router.post("/mz/match")
@api_route(status_code=200)
async def match_cheminfo_mz(body: CheminfoMatchedQueryBody, user=Depends(guest_user)):
    """
    Query the ChemInfo database by mz and other optional parameters.

    :param body: request query options; the only required field is `mz`
    :type body: CheminfoQueryBody
    :rtype dict:
    """
    return await cheminfo_by_mz_matched(
        mz=body.mz,
        sample_item_id=body.sample_item_id,
        mz_precision=body.mz_precision,
        formula_ranges=body.formula_ranges,
        ionization_mechanism_ids=body.ionization_mechanism_ids,
        match_params=body.match_params,
        limit=body.limit,
    )
