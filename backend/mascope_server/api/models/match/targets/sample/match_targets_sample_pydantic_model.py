from typing import Optional
from pydantic import Field
from mascope_server.api.models.base_pydantic_model import QueryParamsModel

# TODO_configuration Default Filter Parameters
DEFAULT_MIN_ISOTOPE_ABUNDANCE = 0.05


class SortingPaginationQueryParams(QueryParamsModel):
    order: Optional[str] = Field(
        "desc",
        description="The sort order, either 'asc' for ascending or 'desc' for descending.",
    )
    page: int = Field(0, description="The page number for pagination.")
    limit: int = Field(10000, description="The number of results per page.")


class GetMatchSampleCompoundsQueryParams(SortingPaginationQueryParams):
    target_collection_id: Optional[str] = Field(
        None, description="The ID of the target collection to filter compounds by."
    )
    deduplicate: Optional[bool] = Field(
        False,
        description="Drop the potential duplicates (added to several target collections). The target collection info is preserved based on collection type priority 'TARGETS' > 'DIAGNOSTICS' > 'CALIBRANTS'",
    )


class GetMatchSampleIonsQueryParams(GetMatchSampleCompoundsQueryParams):
    target_compound_id: Optional[str] = Field(
        None, description="Filter by target compound ID."
    )


class GetMatchSampleIsotopesQueryParams(GetMatchSampleCompoundsQueryParams):
    target_ion_id: Optional[str] = Field(None, description="Filter by target ion ID.")
    min_relative_abundance: Optional[float] = Field(
        DEFAULT_MIN_ISOTOPE_ABUNDANCE,
        description="Filter by  minimum relative abundance of target isotope.",
    )
