from typing import List
from fastapi import APIRouter, Depends
from mascope_server.api.utils.api_features import api_route
from mascope_server.api.controllers.match.match_collections_controller import (
    create_match_collections,
    delete_match_collections,
)
from mascope_server.api.models.pydantic_models.match_collection_pydantic_model import (
    MatchCollectionBase,
    DeleteMatchCollectionsPayload,
)

match_collections_router = APIRouter()


@match_collections_router.post("/api/match/collections")
@api_route(status_code=201)
async def create_match_collections_route(body: List[MatchCollectionBase]):
    return await create_match_collections(
        match_collections=body, independent_transaction=True
    )


@match_collections_router.delete("/api/match/collections")
@api_route()
async def delete_match_collections_route(body: DeleteMatchCollectionsPayload):
    return await delete_match_collections(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
        target_collections_ids=body.target_collections_ids,
    )
