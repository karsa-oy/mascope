from typing import Optional, Dict
from pydantic import BaseModel, Field
from mascope_server.api.models.base_pydantic_model import QueryParamsModel
from mascope_server.api.new.match.params import BaseMatchParams


class TargetIonUpdate(BaseModel):
    match_params: Dict[str, BaseMatchParams] = Field(
        None, description="Ion-specific match parameters"
    )
    delete_instrument_params: Optional[str] = Field(
        None, description="Instrument name which match parameteres to delete"
    )

    class Config:
        from_attributes = True


class GetTargetIonsQueryParams(QueryParamsModel):
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
    show_ionization_mechanism: bool = Field(
        False,
        description="Flag to to include ionization mechanism details.",
    )
    sort: Optional[str] = Field(None, description="Field to sort by.")
    order: Optional[str] = Field(
        None, description="Order of sorting ('asc' or 'desc')."
    )
    page: int = Field(0, description="Pagination page.")
    limit: int = Field(10000, description="Number of items per page.")
