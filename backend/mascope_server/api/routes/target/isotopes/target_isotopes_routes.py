from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.target.isotopes.target_isotopes_controller import (
    get_target_isotope,
    get_target_isotopes,
)
from mascope_server.api.models.target.isotopes.target_isotope_pydantic_model import (
    GetTargetIsotopesQueryParams,
)

target_isotopes_router = APIRouter()


@target_isotopes_router.get("/api/target/isotopes")
@api_route()
async def get_target_isotopes_route(
    query_params: GetTargetIsotopesQueryParams = Depends(),
):
    return await get_target_isotopes(**query_params.model_dump())


@target_isotopes_router.get("/api/target/isotopes/{target_isotope_id}")
@api_route()
async def get_target_isotope_route(target_isotope_id: str):
    return await get_target_isotope(target_isotope_id)
