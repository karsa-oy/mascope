from fastapi import APIRouter, Body
from ..controllers.ionization_mechanisms_controller import (
    get_ionization_mechanisms,
    get_ionization_mechanism,
    create_ionization_mechanism,
)
from ..models.pydantic_models.ionization_mechanism_pydantic_model import (
    IonizationMechanismCreate,
)

ionization_mechanisms_router = APIRouter()


@ionization_mechanisms_router.get("/api/ionization_mechanisms")
async def get_ionization_mechanisms_route(
    ionization_mechanism_polarity: str = None,
    ionization_mechanism: str = None,
    reagent: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_ionization_mechanisms(
        ionization_mechanism_polarity,
        ionization_mechanism,
        reagent,
        sort,
        order,
        page,
        limit,
    )


@ionization_mechanisms_router.get(
    "/api/ionization_mechanisms/{ionization_mechanism_id}"
)
async def get_ionization_mechanism_route(ionization_mechanism_id: str):
    return await get_ionization_mechanism(ionization_mechanism_id)


@ionization_mechanisms_router.post("/api/ionization_mechanisms")
async def create_ionization_mechanism_route(
    ionization_mechanism: IonizationMechanismCreate = Body(...),
):
    return await create_ionization_mechanism(ionization_mechanism)
