from datetime import datetime
from pydantic import Field
from mascope_backend.api.models.base_pydantic_model import (
    QueryParamsModel,
    CommonValidators,
)

# TODO_configuration
DEFAULT_PEAK_MZ_TOLERANCE_PPM = 1.0


class GetSamplesQueryParams(CommonValidators, QueryParamsModel):
    """
    This model defines the query parameters that can be passed to the GET /api/samples endpoint
    to control filtering, sorting, ordering, and pagination of sample results.
    """

    sample_item_id: str | None = Field(
        None, description="ID of the specific sample item to filter results by"
    )
    sample_file_id: str | None = Field(
        None, description="ID of the sample file to filter results by"
    )
    sample_batch_id: str | None = Field(
        None,
        description="ID of the sample batch to filter results by. Required for batch match info",
    )
    filename: str | None = Field(
        None, description="Filename of the sample to filter results by"
    )
    instrument: str | None = Field(
        None, description="Instrument name to filter results by"
    )
    sample_item_type: str | None = Field(
        None, description="Type of the sample item to filter results by"
    )
    datetime_min: datetime | None = Field(
        None, description="Minimum datetime of the sample file to filter results by"
    )
    datetime_max: datetime | None = Field(
        None, description="Maximum datetime of the sample file to filter results by"
    )
    polarity: str | None = Field(
        None,
        description="Ion polarity mode of the sample item to filter by, either '+' for positive ion mode or '-' for negative ion mode",
    )
    match_category_min: int | None = Field(
        None,
        description="Filter samples by match_category to include samples with specified match category and higher",
    )
    sort: str | None = Field(
        "datetime_utc",
        description="Column name by which to sort the results. Default is 'datetime_utc'",
    )
    order: str | None = Field(
        "asc",
        description="Sorting order, either 'asc' for ascending or 'desc' for descending. Default is 'asc'",
    )
    page: int = Field(0, description="Page number for pagination. Default is 0")
    limit: int = Field(
        10000, description="Number of results per page. Default is 10000"
    )
