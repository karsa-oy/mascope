from fastapi import APIRouter
from ..controllers.match_interferences_controller import (
    get_match_interference_by_id,
    get_match_interferences,
    delete_match_interferences,
)

match_interferences_router = APIRouter()


@match_interferences_router.get("/api/match_interferences")
async def get_match_interferences_route(
    target_isotope_id: str = None,
    sample_item_id: str = None,
    min_sample_peak_interference: float = None,
    max_sample_peak_interference: float = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_match_interferences(
        target_isotope_id,
        sample_item_id,
        min_sample_peak_interference,
        max_sample_peak_interference,
        sort,
        order,
        page,
        limit,
    )


@match_interferences_router.get("/api/match_interferences/{match_interference_id}")
async def get_match_interference_by_id_route(match_interference_id: str):
    return await get_match_interference_by_id(match_interference_id)


@match_interferences_router.delete("/api/match_interferences/{sample_item_id}")
async def delete_match_interferences_route(sample_item_id: str):
    await delete_match_interferences(sample_item_id)
    return {"status": "Match interferences successfully deleted"}
