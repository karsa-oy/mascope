from fastapi import APIRouter, Depends
from ..utils.api_features import api_route
from ..controllers.target_ions_controller import (
    get_target_ions,
    get_target_ion,
    update_target_ion,
)
from ..models.pydantic_models.target_ion_pydantic_model import (
    TargetIonUpdate,
    GetTargetIonsQueryParams,
)

target_ions_router = APIRouter()


@target_ions_router.get("/api/target_ions")
@api_route()
async def get_target_ions_route(
    query_params: GetTargetIonsQueryParams = Depends(),
):
    return await get_target_ions(**query_params.model_dump())


@target_ions_router.get("/api/target_ions/{target_ion_id}")
@api_route()
async def get_target_ion_route(target_ion_id: str):
    return await get_target_ion(target_ion_id=target_ion_id)


@target_ions_router.patch("/api/target_ions/{target_ion_id}")
@api_route(include_message=True, success_message="Target ion updated successfully")
async def update_target_ion_route(
    target_ion_id: str, target_ion_update: TargetIonUpdate
):
    return await update_target_ion(
        target_ion_id=target_ion_id, target_ion_update=target_ion_update
    )
