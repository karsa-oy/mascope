from fastapi import APIRouter
from ..controllers.ionization_mechanisms_controller import (
    get_ionization_mechanism_by_id,
    get_ionization_mechanisms,
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
async def get_ionization_mechanism_by_id_route(ionization_mechanism_id: str):
    return await get_ionization_mechanism_by_id(ionization_mechanism_id)
