from fastapi import APIRouter, Depends
from ..controllers.samples_controller import init_match_filter, load_samples
from ..models.pydantic_models.sample_pydantic_model import (
    MatchFilterBody,
    FilterParams,
    LoadSamplesBody,
)

samples_router = APIRouter()


@samples_router.post("/api/samples/init_match_filter")
async def init_match_filter_route(body: MatchFilterBody):
    result_df = await init_match_filter(body.batch_id, body.filter_params)
    result = result_df.to_dict(orient="records")  # Convert DataFrame to list of dicts
    #     return {"message": "Batch match filter successfully initialized"}
    return {
        "results": len(result),
        "data": result,
    }


@samples_router.get("/api/samples/load_samples/{batch_id}/{sample_item_active_id}")
async def load_samples_route(
    batch_id: str, sample_item_active_id: str, filter_params: FilterParams = Depends()
):
    result = await load_samples(batch_id, sample_item_active_id, filter_params)
    return {
        "results": len(result),
        "data": result,
    }


@samples_router.post("/api/samples/load_samples")
async def load_samples_route(body: LoadSamplesBody):
    result = await load_samples(
        body.batch_id, body.sample_item_active_id, body.filter_params
    )
    return {
        "results": len(result),
        "data": result,
    }
