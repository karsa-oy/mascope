from fastapi import APIRouter

from ..controllers.matches_controller import (
    get_match_by_id,
    get_matches,
)

matches_router = APIRouter()


@matches_router.get("/api/matches")
async def get_matches_route(
    sample_item_id: str = None,
    target_isotope_id: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_matches(
        sample_item_id, target_isotope_id, sort, order, page, limit
    )


@matches_router.get("/api/matches/{match_id}")
async def get_match_by_id_route(match_id: str):
    return await get_match_by_id(match_id)
