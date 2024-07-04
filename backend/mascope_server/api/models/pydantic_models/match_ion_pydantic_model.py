from pydantic import BaseModel, Field
from typing import Optional, List
from mascope_server.api.models.pydantic_models.match_pydantic_model import (
    FilterSamplePayload,
)


class MatchIonBase(BaseModel):
    sample_item_id: str = Field(..., description="Foreign key to sample_item")
    target_ion_id: str = Field(..., description="Foreign key to target_ion")
    match_score: float = Field(..., description="Score of the match ion")
    match_category: int = Field(..., description="Category of the match")
    sample_peak_area_sum: float = Field(..., description="Area of the sample peak")
    sample_peak_interference_sum: float = Field(
        ..., description="Area of the sample peak"
    )


class DeleteMatchIonsPayload(FilterSamplePayload):
    target_ion_ids: Optional[List[str]] = Field(
        None,
        description="Optional list of target ion IDs to limit the match ions being deleted.",
    )
