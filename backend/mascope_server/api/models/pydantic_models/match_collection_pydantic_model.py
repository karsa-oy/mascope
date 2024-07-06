from pydantic import BaseModel, Field
from typing import Optional, List
from mascope_server.api.models.pydantic_models.match_pydantic_model import (
    FilterSamplePayload,
)


class MatchCollectionBase(BaseModel):
    sample_item_id: str = Field(..., description="Foreign key to sample_item")
    target_collection_id: str = Field(
        ..., description="Foreign key to target_collection"
    )
    match_score: float = Field(..., description="Score of the match")
    match_category: int = Field(..., description="Category of the match")
    sample_peak_area_sum: float = Field(
        ..., description="Sum of the area of the sample peak"
    )
    sample_peak_interference_sum: float = Field(
        ..., description="Sum of the area of the sample peak interference"
    )


class DeleteMatchCollectionsPayload(FilterSamplePayload):
    target_collections_ids: Optional[List[str]] = Field(
        None,
        description="Optional list of target collection IDs to limit the match collections being deleted.",
    )
