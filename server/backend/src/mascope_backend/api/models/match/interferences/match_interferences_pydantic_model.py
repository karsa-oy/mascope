from typing import Optional, List
from pydantic import BaseModel, Field
from mascope_backend.api.models.base_pydantic_model import QueryParamsModel
from mascope_backend.api.models.match.match_pydantic_model import (
    FilterSamplePayload,
)


class MatchInterferenceBase(BaseModel):
    match_interference_id: str = Field(
        ..., description="ID of match interference, primary key"
    )
    target_isotope_id: str = Field(..., description="Foreign key to target_isotope")
    sample_item_id: str = Field(..., description="Foreign key to sample_item")
    sample_peak_interference: float = Field(..., description="Sample peak interference")


class GetMatchInterferencesQueryParams(QueryParamsModel):
    target_isotope_id: Optional[str] = Field(
        None, description="Filter by the ID of the target isotope"
    )
    sample_item_id: Optional[str] = Field(
        None, description="Filter by the ID of the sample item"
    )
    sample_batch_id: Optional[str] = Field(
        None, description="The ID of the sample batch to filter match interferences by."
    )
    min_sample_peak_interference: Optional[float] = Field(
        None, description="Filter by the Minimum sample peak interference"
    )
    max_sample_peak_interference: Optional[float] = Field(
        None, description="Filter by the Maximum sample peak interference"
    )
    sort: Optional[str] = Field(None, description="Field to sort by")
    order: Optional[str] = Field(None, description="Order of sorting ('asc' or 'desc')")
    page: int = Field(0, description="Pagination page number")
    limit: int = Field(1000000, description="Number of items per page")


class DeleteMatchInterferencesPayload(FilterSamplePayload):
    target_isotope_ids: Optional[List[str]] = Field(
        None,
        description="Optional list of target isotope IDs to limit the match interferences being deleted.",
    )
