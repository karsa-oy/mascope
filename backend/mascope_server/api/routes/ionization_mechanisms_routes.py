from fastapi import APIRouter, Depends, Body
from ..utils.api_features import api_route
from ..controllers.ionization_mechanisms_controller import (
    get_ionization_mechanisms,
    get_ionization_mechanism,
    create_ionization_mechanism,
    delete_ionization_mechanism,
)
from ..models.pydantic_models.ionization_mechanism_pydantic_model import (
    IonizationMechanismCreate,
    GetIonizationMechanismsQueryParams,
)

ionization_mechanisms_router = APIRouter()


@ionization_mechanisms_router.get("/api/ionization_mechanisms")
@api_route()
async def get_ionization_mechanisms_route(
    query_params: GetIonizationMechanismsQueryParams = Depends(),
):
    return await get_ionization_mechanisms(**query_params.model_dump())


@ionization_mechanisms_router.get(
    "/api/ionization_mechanisms/{ionization_mechanism_id}"
)
@api_route()
async def get_ionization_mechanism_route(ionization_mechanism_id: str):
    return await get_ionization_mechanism(ionization_mechanism_id)


@ionization_mechanisms_router.post("/api/ionization_mechanisms")
@api_route(
    status_code=201,
    include_message=True,
    success_message="Ionization mechanism created successfully",
)
async def create_ionization_mechanism_route(
    ionization_mechanism: IonizationMechanismCreate = Body(...),
):
    return await create_ionization_mechanism(ionization_mechanism)


@ionization_mechanisms_router.delete(
    "/api/ionization_mechanisms/{ionization_mechanism_id}"
)
@api_route()
async def delete_ionization_mechanism_route(ionization_mechanism_id: str):
    return await delete_ionization_mechanism(ionization_mechanism_id)
