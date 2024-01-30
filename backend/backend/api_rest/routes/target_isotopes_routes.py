from fastapi import APIRouter, Query
from typing import List, Optional

from ..controllers.target_isotopes_controller import (
    get_target_isotope,
    get_target_isotopes,
)

target_isotopes_router = APIRouter()


@target_isotopes_router.get("/api/target_isotopes")
async def get_target_isotopes_route(
    target_ion_id: str = Query(None, description="Filter by target ion ID."),
    min_mz: float = Query(None, description="Minimum m/z value for filtering."),
    max_mz: float = Query(None, description="Maximum m/z value for filtering."),
    min_relative_abundance: float = Query(
        None, description="Minimum relative abundance for filtering."
    ),
    max_relative_abundance: float = Query(
        None, description="Maximum relative abundance for filtering."
    ),
    target_compound_ids: List[str] = Query(
        default=[], description="List of target compound IDs to filter isotopes."
    ),
    ionization_mechanism_ids: List[str] = Query(
        default=[], description="List of ionization mechanism IDs to filter isotopes."
    ),
    sample_batch_id: str = Query(
        None,
        description="ID of the sample batch for filtering the associated to batch isotopes.",
    ),
    sort: str = Query(None, description="Field to sort by."),
    order: str = Query(None, description="Order of sorting ('asc' or 'desc')."),
    page: int = Query(0, description="Pagination page."),
    limit: int = Query(1000000, description="Number of items per page."),
):
    return await get_target_isotopes(
        target_ion_id,
        min_mz,
        max_mz,
        min_relative_abundance,
        max_relative_abundance,
        target_compound_ids,
        ionization_mechanism_ids,
        sample_batch_id,
        sort,
        order,
        page,
        limit,
    )


@target_isotopes_router.get("/api/target_isotopes/{target_isotope_id}")
async def get_target_isotope_route(target_isotope_id: str):
    return await get_target_isotope(target_isotope_id)
