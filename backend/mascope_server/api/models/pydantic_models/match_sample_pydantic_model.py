from pydantic import BaseModel, Field


class MatchSampleBase(BaseModel):
    sample_item_id: str = Field(..., description="Foreign key to sample_item")
    match_score: float = Field(..., description="Score of the match")
    match_category: int = Field(..., description="Category of the match")
    sample_peak_area_sum: float = Field(
        ..., description="Sum of the area of the sample peak"
    )
    sample_peak_interference_sum: float = Field(
        ..., description="Sum of the area of the sample peak interference"
    )
