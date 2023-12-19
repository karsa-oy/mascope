from fastapi import APIRouter, Query, Body

from ..controllers.target_ions_controller import (
    get_target_ions,
    get_target_ion,
    update_target_ion,
)
from ..models.pydantic_models.target_ion_pydantic_model import TargetIonUpdate

target_ions_router = APIRouter()


@target_ions_router.get("/api/target_ions")
async def get_target_ions_route(
    target_compound_id: str = None,
    ionization_mechanism_id: str = None,
    target_ion_formula: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_target_ions(
        target_compound_id,
        ionization_mechanism_id,
        target_ion_formula,
        sort,
        order,
        page,
        limit,
    )


@target_ions_router.get("/api/target_ions/{target_ion_id}")
async def get_target_ion_route(
    target_ion_id: str,
):
    return await get_target_ion(
        target_ion_id=target_ion_id,
    )


@target_ions_router.patch("/api/target_ions/{target_ion_id}")
async def update_target_collection_route(
    target_ion_id: str,
    target_ion_update: TargetIonUpdate = Body(...),
):
    return await update_target_ion(target_ion_id, target_ion_update)
