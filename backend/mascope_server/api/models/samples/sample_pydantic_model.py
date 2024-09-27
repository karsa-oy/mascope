from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class GetSamplesQueryParams(BaseModel):
    sample_item_id: Optional[str] = Field(
        None, description="ID of the specific sample item to filter results by."
    )
    sample_file_id: Optional[str] = Field(
        None, description="ID of the sample file to filter results by."
    )
    sample_batch_id: Optional[str] = Field(
        None,
        description="ID of the sample batch to filter results by. Required for batch match info.",
    )
    filename: Optional[str] = Field(
        None, description="Filename of the sample to filter results by."
    )
    instrument: Optional[str] = Field(
        None, description="Instrument name to filter results by."
    )
    sample_item_type: Optional[str] = Field(
        None, description="Type of the sample item to filter results by."
    )
    datetime_min: Optional[datetime] = Field(
        None, description="Minimum datetime of the sample file to filter results by."
    )
    datetime_max: Optional[datetime] = Field(
        None, description="Maximum datetime of the sample file to filter results by."
    )
    match_category: Optional[int] = Field(
        None, description="Filter match samples by match category"
    )
    sort: Optional[str] = Field(
        "datetime_utc",
        description="Column name by which to sort the results. Default is 'datetime_utc'.",
    )
    order: Optional[str] = Field(
        "asc",
        description="Sorting order, either 'asc' for ascending or 'desc' for descending. Default is 'asc'.",
    )
    page: Optional[int] = Field(
        0, description="Page number for pagination. Default is 0."
    )
    limit: Optional[int] = Field(
        10000, description="Number of results per page. Default is 10000."
    )
