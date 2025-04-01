from pydantic import BaseModel, Field

from mascope_backend.api.new.match.params import BaseMatchParams


class CheminfoQueryBody(BaseModel):
    mz: float = Field(..., description="The mz to query ChemCalc for")
    mz_precision: int = Field(
        1000,
        description="The precision of mz values, i.e. the query returns matches between mz +/- mzPrecision",
    )
    formula_ranges: str | None = Field(
        None,
        description="The formula range to query, defaults to 'C0-100 H0-100 O0-100 N0-100'",
    )
    ionization_mechanism_ids: list[str] | None = Field(
        None, description="The ionization mechanisms ids to query against"
    )
    limit: int = Field(20, description="Limit of the number of results to return")


class CheminfoMatchedQueryBody(CheminfoQueryBody):
    sample_item_id: str = (
        Field(..., description="The sample item ID to match against"),
    )
    match_params: BaseMatchParams | None = Field(
        None, description="Match parameters to use"
    )
