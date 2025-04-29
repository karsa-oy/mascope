from pydantic import BaseModel, Field

from mascope_backend.api.new.match.params import BaseMatchParams
from mascope_backend.api.new.cheminfo.config import cheminfo_config


class CheminfoQueryBody(BaseModel):
    mz: float = Field(..., description="The m/z value to query ChemInfo for")
    mz_precision: float = Field(
        cheminfo_config.DEFAULT_MZ_PRECISION,
        description="The precision (tolerance in ppm) for m/z matching, i.e. the query returns matches between m/z +/- m/z precision",
    )
    formula_ranges: None | str = Field(
        None,
        description="The formula range to query, defaults to 'C0-100 H0-100 O0-100 N0-100'",
    )
    ionization_mechanism_ids: None | list[str] = Field(
        None, description="The ionization mechanism IDs to query against"
    )
    page: int = Field(
        cheminfo_config.DEFAULT_PAGE,
        description="The page number for pagination",
    )
    limit: int = Field(
        cheminfo_config.DEFAULT_RESULT_LIMIT,
        description="Maximum number of results to return per page",
    )
    sort: None | str = Field(
        None,
        description="The field to sort results by",
    )
    order: None | str = Field(
        None,
        description="Sort order: 'asc' for ascending or 'desc' for descending",
    )


class CheminfoMatchedQueryBody(CheminfoQueryBody):
    sample_item_id: str = (
        Field(..., description="The sample item ID to match against"),
    )
    match_params: BaseMatchParams | None = Field(
        None, description="Match parameters to use"
    )
