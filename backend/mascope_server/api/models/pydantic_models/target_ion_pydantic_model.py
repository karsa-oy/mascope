from pydantic import BaseModel, Field
from typing import Optional, Dict
from .match_pydantic_model import FilterParams


class TargetIonUpdate(BaseModel):
    filter_params: Dict[str, FilterParams] = Field(
        None, description="Ion-specific filter parameters"
    )
    delete_instrument_filters: Optional[str] = Field(
        None, description="Instrument name which filter parameteres to delete"
    )

    class Config:
        orm_mode = True


class GetTargetIonsQueryParams(BaseModel):
    target_compound_id: Optional[str] = Field(
        None, description="Filter by target compound ID."
    )
    ionization_mechanism_id: Optional[str] = Field(
        None, description="Filter by ionization mechanism ID."
    )
    target_ion_formula: Optional[str] = Field(
        None, description="Filter by target ion formula."
    )
    sample_batch_id: Optional[str] = Field(
        None, description="The ID of the sample batch to filter ions by."
    )
    target_collection_id: Optional[str] = Field(
        None, description="The ID of the target collection to filter ions by."
    )
    show_target_collection: bool = Field(
        False,
        description="Flag to include target collection ID, also duplicate compounds present in several collections will be shown.",
    )
    sort: Optional[str] = Field(None, description="Field to sort by.")
    order: Optional[str] = Field(
        None, description="Order of sorting ('asc' or 'desc')."
    )
    page: int = Field(0, description="Pagination page.")
    limit: int = Field(10000, description="Number of items per page.")
