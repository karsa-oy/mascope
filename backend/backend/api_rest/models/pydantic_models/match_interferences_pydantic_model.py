from pydantic import BaseModel, Field
from typing import Optional


class GetMatchInterferencesQueryParams(BaseModel):
    target_isotope_id: Optional[str] = Field(
        None, description="Filter by the ID of the target isotope"
    )
    sample_item_id: Optional[str] = Field(
        None, description="Filter by the ID of the sample item"
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
