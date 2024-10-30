from typing import Optional
from pydantic import BaseModel, Field
from mascope_server.api.new.match.params import (
    TofMatchParams,
    OrbiMatchParams,
)
from mascope_server.api.models.target.compounds.target_compound_pydantic_model import (
    TargetCompoundMatches,
)


class AggregateMatchIsotopeFilteredDataBody(BaseModel):
    target_ion_id: str = Field(
        None, description="Filter targets by ID of the target ion"
    )
    match_params: TofMatchParams | OrbiMatchParams = Field(
        None,
        description="Ion-specific filter parameters, used for match_score and sample_peak_area filtering, setting match_category",
    )
    include_match_interference: bool = Field(
        True, description="Include match interference data in the response"
    )


class AggregateSampleMatchIonBody(BaseModel):
    target_ion_id: str = Field(..., description="ID of the target ion")
    target_collection_id: str = Field(
        ..., description="ID of the target collection to remove possible dublicates"
    )
    match_params: TofMatchParams | OrbiMatchParams = Field(
        None,
        description="Ion-specific filter parameters, used for match_score and sample_peak_area filtering",
    )


class AggregateSampleMatchCompoundBody(BaseModel):
    target_compound: TargetCompoundMatches = Field(
        ..., description="Target compound with required formula and optional name"
    )
    match_params: TofMatchParams | OrbiMatchParams = Field(
        None,
        description="Sample-specific filter parameters, used for match_score and sample_peak_area filtering",
    )


class AggregateAndCreateMatchesBody(AggregateMatchIsotopeFilteredDataBody):
    match_ions: Optional[bool] = Field(
        True, description="Flag to determine if ion matches should be processed"
    )
    match_compounds: Optional[bool] = Field(
        True, description="Flag to determine if compound matches should be processed"
    )
    match_collections: Optional[bool] = Field(
        True, description="Flag to determine if collection matches should be processed"
    )
    match_samples: Optional[bool] = Field(
        True, description="Flag to determine if sample matches should be processed"
    )
