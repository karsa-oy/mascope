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
@api_route(status_code=200)
async def query_cheminfo_mz(body: CheminfoQueryBody, user=Depends(guest_user)):
    """
    Query the ChemInfo database by mz and other optional parameters.

    :param body: request query options; the only required field is `mz`
    :type body: CheminfoQueryBody
    :rtype dict:
    """
    return await cheminfo_by_mz(
        mz=body.mz,
        mz_precision=body.mz_precision,
        formula_ranges=body.formula_ranges,
        ionization_mechanism_ids=body.ionization_mechanism_ids,
        limit=body.limit,
    )


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
