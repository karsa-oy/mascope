from typing import Optional

from pydantic import BaseModel, Field, field_validator

from mascope_backend.api.models.target.compounds.target_compound_pydantic_model import (
    TargetCompoundMatches,
    validate_compound_formula,
)
from mascope_match.params import (
    OrbiMatchParams,
    TofMatchParams,
)


class AggregateMatchIsotopeFilteredDataBody(BaseModel):
    target_ion_id: str = Field(
        None, description="Filter targets by ID of the target ion"
    )
    match_params: TofMatchParams | OrbiMatchParams = Field(
        None,
        description="Ion-specific filter parameters, used for match_score and sample_peak_intensity filtering, setting match_category",
    )


class AggregateSampleMatchIonBody(BaseModel):
    target_ion_id: str = Field(..., description="ID of the target ion")
    target_collection_id: str = Field(
        ..., description="ID of the target collection to remove possible dublicates"
    )
    match_params: TofMatchParams | OrbiMatchParams = Field(
        None,
        description="Ion-specific filter parameters, used for match_score and sample_peak_intensity filtering",
    )


class AggregateSampleMatchCompoundBody(BaseModel):
    target_compound: TargetCompoundMatches = Field(
        ..., description="Target compound with required formula and optional name"
    )
    match_params: TofMatchParams | OrbiMatchParams = Field(
        None,
        description="Sample-specific filter parameters, used for match_score and sample_peak_intensity filtering",
    )


class AggregateSampleMatchCompoundsBody(BaseModel):
    target_compound_formulas: list[str] = Field(
        ..., description="Target compound formulas to match and aggregate"
    )
    match_params: TofMatchParams | OrbiMatchParams = Field(
        None,
        description="Sample-specific filter parameters, used for match_score and sample_peak_area filtering",
    )
    ion_mechanism_ids: list[str] | None = Field(
        None,
        description="List of ion mechanism ids to use; if none are provided, sample batch defaults are used.",
    )

    @field_validator("target_compound_formulas")
    @classmethod
    def _validate_formulas(cls, formulas: list[str]) -> list[str]:
        # This endpoint builds TargetCompound rows directly (bypassing the
        # TargetCompound model), so apply the same formula validation here;
        # otherwise a numeric mass or invalid formula silently yields
        # adduct-only ions or a compound that can never match.
        for formula in formulas:
            validate_compound_formula(formula)
        return formulas


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
