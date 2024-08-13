from typing import Optional, List
from pydantic import BaseModel, Field
from mascope_server.api.models.match.match_pydantic_model import (
    FilterSamplePayload,
)


class MatchCompoundBase(BaseModel):
    sample_item_id: str = Field(..., description="Foreign key to sample_item")
    target_compound_id: str = Field(..., description="Foreign key to target_compound")
    match_score: float = Field(..., description="Score of the match")
    match_category: int = Field(..., description="Category of the match")
    sample_peak_area_sum: float = Field(
        ..., description="Sum of the area of the sample peak"
    )
    sample_peak_interference_sum: float = Field(
        ..., description="Sum of the area of the sample peak interference"
    )


class GetMatchCompoundsQueryParams(BaseModel):
    sample_item_id: Optional[str] = Field(
        None, description="Filter compounds by sample item ID"
    )
    sample_batch_id: Optional[str] = Field(
        None, description="The ID of the sample batch to filter compounds by."
    )
    target_compound_id: Optional[str] = Field(
        None, description="Filter compounds by target compound ID"
    )
    match_category: Optional[int] = Field(
        None, description="Filter compounds by match category"
    )
    show_target_collection: bool = Field(
        False,
        description="Flag to include target collection ID, also duplicate compounds present in several collections will be shown.",
    )
    show_target_compound: bool = Field(
        False,
        description="Flag to include target compound name, used for BatchOverview.",
    )
    sort: Optional[str] = Field(
        None, description="The column name to sort the results by."
    )
    order: Optional[str] = Field(
        None,
        description="The sort order, either 'asc' for ascending or 'desc' for descending.",
    )
    page: int = Field(0, description="The page number for pagination.")
    limit: int = Field(10000, description="The number of results per page.")


class DeleteMatchCompounsPayload(FilterSamplePayload):
    target_compound_ids: Optional[List[str]] = Field(
        None,
        description="Optional list of target compound IDs to limit the match compounds being deleted.",
    )
