from pydantic import BaseModel, Field
from typing import Optional


class GetMatchesQueryParams(BaseModel):
    sample_item_id: Optional[str] = Field(
        None, description="Filter by the ID of the sample item"
    )
    target_isotope_id: Optional[str] = Field(
        None, description="Filter by the ID of the target isotope"
    )
    sort: Optional[str] = Field(None, description="Field to sort by")
    order: Optional[str] = Field(None, description="Order of sorting ('asc' or 'desc')")
    page: int = Field(0, description="Pagination page number")
    limit: int = Field(1000000, description="Number of items per page")
