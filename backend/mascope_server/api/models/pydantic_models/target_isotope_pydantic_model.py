from typing import List, Optional
from pydantic import BaseModel, Field


class GetTargetIsotopesQueryParams(BaseModel):
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
    show_filter_params: bool = Field(
        False,
        description="Flag to include filter_params of the isotope's parent target ion.",
    )
    sort: Optional[str] = Field(None, description="Field to sort by.")
    order: Optional[str] = Field(
        None, description="Order of sorting ('asc' or 'desc')."
    )
    page: int = Field(0, description="Pagination page.")
    limit: int = Field(1000000, description="Number of items per page.")
