from fastapi import APIRouter, Depends
from ..utils.api_features import api_route
from ..controllers.target_isotopes_controller import (
    get_target_isotope,
    get_target_isotopes,
)
from ..models.pydantic_models.target_isotope_pydantic_model import (
    GetTargetIsotopesQueryParams,
)

target_isotopes_router = APIRouter()


@target_isotopes_router.get("/api/target_isotopes")
@api_route()
async def get_target_isotopes_route(
    query_params: GetTargetIsotopesQueryParams = Depends(),
):
    return await get_target_isotopes(**query_params.dict())


@target_isotopes_router.get("/api/target_isotopes/{target_isotope_id}")
@api_route()
async def get_target_isotope_route(target_isotope_id: str):
    return await get_target_isotope(target_isotope_id)
