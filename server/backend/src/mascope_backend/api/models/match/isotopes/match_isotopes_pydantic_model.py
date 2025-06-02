from typing import Optional, List
from pydantic import BaseModel, Field
from mascope_backend.api.models.base_pydantic_model import QueryParamsModel
from mascope_backend.api.models.match.match_pydantic_model import (
    FilterSamplePayload,
)


class MatchIsotopeBase(BaseModel):
    match_isotope_id: str = Field(..., description="ID of match isotope, primary key")
    target_isotope_id: str = Field(..., description="Foreign key to target_isotope")
    sample_item_id: str = Field(..., description="Foreign key to sample_item")
    sample_peak_id: int = Field(..., description="ID of the sample peak")
    sample_peak_mz: float = Field(
        ..., description="Mass-to-charge ratio of the sample peak"
    )
    sample_peak_intensity: float = Field(
        ..., description="Intensity of the sample peak"
    )
    sample_peak_intensity_relative: float = Field(
        ..., description="Relative intensity of the sample peak"
    )
    sample_peak_tof: float = Field(..., description="Time-of-flight of the sample peak")
    match_abundance_error: float = Field(
        ..., description="Abundance error of the match"
    )
    match_mz_error: float = Field(
        ..., description="Mass-to-charge ratio error of the match"
    )
    match_isotope_similarity: float = Field(
        ..., description="Similarity of the isotope match"
    )
    match_score: float = Field(..., description="Score of the match")


class GetMatchesQueryParams(QueryParamsModel):
    sample_item_id: Optional[str] = Field(
        None, description="Filter by the ID of the sample item"
    )
    sample_batch_id: Optional[str] = Field(
        None, description="The ID of the sample batch to filter match isotopes by."
    )
    target_isotope_id: Optional[str] = Field(
        None, description="Filter by the ID of the target isotope"
    )
    show_target_isotope: bool = Field(
        False,
        description="Flag to include target isotope details.",
    )
    sort: Optional[str] = Field(None, description="Field to sort by")
    order: Optional[str] = Field(None, description="Order of sorting ('asc' or 'desc')")
    page: int = Field(0, description="Pagination page number")
    limit: int = Field(1000000, description="Number of items per page")


class DeleteMatchIsotopesPayload(FilterSamplePayload):
    target_isotope_ids: Optional[List[str]] = Field(
        None,
        description="Optional list of target isotope IDs to limit the match isotopes being deleted.",
    )
