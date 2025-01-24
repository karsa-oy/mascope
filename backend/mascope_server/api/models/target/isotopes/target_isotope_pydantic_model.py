from typing import List, Optional
from pydantic import Field, field_validator
from mascope_server.api.models.base_pydantic_model import QueryParamsModel


ISOTOPE_RESOLUTION_TYPES = ["HIGH", "LOW", None]


class GetTargetIsotopesQueryParams(QueryParamsModel):
    target_ion_id: Optional[str] = Field(None, description="Filter by target ion ID.")
    min_mz: Optional[float] = Field(
        None, description="Minimum m/z value for filtering."
    )
    max_mz: Optional[float] = Field(
        None, description="Maximum m/z value for filtering."
    )
    min_relative_abundance: Optional[float] = Field(
        None, description="Minimum relative abundance for filtering."
    )
    max_relative_abundance: Optional[float] = Field(
        None, description="Maximum relative abundance for filtering."
    )
    resolution: Optional[str] = Field(
        None, description="Type of the target isotope resolution, LOW or HIGH"
    )
    target_compound_ids: List[str] = Field(
        default=[], description="List of target compound IDs to filter isotopes."
    )
    ionization_mechanism_ids: List[str] = Field(
        default=[], description="List of ionization mechanism IDs to filter isotopes."
    )
    sample_batch_id: Optional[str] = Field(
        None,
        description="ID of the sample batch for filtering the associated to batch isotopes.",
    )
    target_collection_id: Optional[str] = Field(
        None, description="The ID of the target collection to filter ions by."
    )
    show_target_collection: bool = Field(
        False,
        description="Flag to include target collection ID, also duplicate compounds present in several collections will be shown.",
    )
    show_match_params: bool = Field(
        False,
        description="Flag to include match_params of the isotope's parent target ion.",
    )
    sort: Optional[str] = Field(None, description="Field to sort by.")
    order: Optional[str] = Field(
        None, description="Order of sorting ('asc' or 'desc')."
    )
    page: int = Field(0, description="Pagination page.")
    limit: int = Field(1000000, description="Number of items per page.")

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, resolution):
        """Ensure isotope `resolution` is one of the allowed types."""
        if resolution not in ISOTOPE_RESOLUTION_TYPES:
            allowed_types = ", ".join(ISOTOPE_RESOLUTION_TYPES)
            raise ValueError(
                f"Invalid isotope resolution type '{resolution}'. Allowed types are: {allowed_types}."
            )
        return resolution
