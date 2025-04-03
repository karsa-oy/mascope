from typing import Optional
from pydantic import Field
from mascope_backend.api.models.base_pydantic_model import QueryParamsModel


class SortingPaginationQueryParams(QueryParamsModel):
    order: Optional[str] = Field(
        "desc",
        description="The sort order, either 'asc' for ascending or 'desc' for descending.",
    )
    page: int = Field(0, description="The page number for pagination.")
    limit: int = Field(10000, description="The number of results per page.")


class GetMatchBatchCompoundsQueryParams(SortingPaginationQueryParams):
    target_collection_id: Optional[str] = Field(
        None, description="The ID of the target collection to filter compounds by."
    )


class GetMatchBatchIonsQueryParams(GetMatchBatchCompoundsQueryParams):
    target_compound_id: Optional[str] = Field(
        None, description="Filter by target compound ID."
    )


class GetMatchBatchIsotopesQueryParams(GetMatchBatchCompoundsQueryParams):
    target_ion_id: Optional[str] = Field(None, description="Filter by target ion ID.")
    min_relative_abundance: Optional[float] = Field(
        None,
        description="Filter by  minimum relative abundance of target isotope.",
    )
