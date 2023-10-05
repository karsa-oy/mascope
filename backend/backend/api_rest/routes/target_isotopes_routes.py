from fastapi import APIRouter
from ..controllers.target_isotopes_controller import (
    get_target_isotope_by_id,
    get_target_isotopes,
)

target_isotopes_router = APIRouter()


@target_isotopes_router.get("/api/target_isotopes")
async def get_target_isotopes_route(
    target_ion_id: str = None,
    min_mz: float = None,
    max_mz: float = None,
    min_relative_abundance: float = None,
    max_relative_abundance: float = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_target_isotopes(
        target_ion_id,
        min_mz,
        max_mz,
        min_relative_abundance,
        max_relative_abundance,
        sort,
        order,
        page,
        limit,
    )


@target_isotopes_router.get("/api/target_isotopes/{target_isotope_id}")
async def get_target_isotope_by_id_route(target_isotope_id: str):
    return await get_target_isotope_by_id(target_isotope_id)
