from typing import Optional
from pydantic import BaseModel, Field


class TargetCompoundBase(BaseModel):
    target_compound_id: Optional[str] = Field(
        None, description="ID of the target compound"
    )
    target_compound_name: Optional[str] = Field(
        "", description="Name of the target compound"
    )
    target_compound_formula: str = Field(
        ..., description="Formula of the target compound"
    )
    cas_number: Optional[str] = Field(
        None, description="CAS Number of the target compound"
    )


class TargetCompoundMatches(TargetCompoundBase):
    target_compound_name: Optional[str] = Field(
        "Unknown Compound", description="Name of the target compound"
    )


class TargetCompoundUpdate(BaseModel):
    target_compound_id: str = Field(..., description="ID of the target compound")
    target_collection_id: Optional[str] = Field(
        None, description="ID of the target collection"
    )
    target_compound_name: Optional[str] = Field(
        "", description="Name of the target compound"
    )
    target_compound_formula: Optional[str] = Field(
        None, description="Formula of the target compound"
    )
    cas_number: Optional[str] = Field(
        None, description="CAS Number of the target compound"
    )


class GetTargetCompoundsQueryParams(BaseModel):
    target_compound_name: Optional[str] = Field(
        None, description="The name of the target compound to filter by."
    )
    target_compound_formula: Optional[str] = Field(
        None, description="The formula of the target compound to filter by."
    )
    sample_batch_id: Optional[str] = Field(
        None, description="The ID of the sample batch to filter compounds by."
    )
    target_collection_id: Optional[str] = Field(
        None, description="The ID of the target collection to filter compounds by."
    )
    show_target_collection: bool = Field(
        False,
        description="Flag to include target collection ID, also duplicate compounds present in several collections will be shown.",
    )
    sort: Optional[str] = Field(
        None, description="The column name to sort the results by."
    )
    order: Optional[str] = Field(
        None,
        description="The sort order, either 'asc' for ascending or 'desc' for descending.",
    )
    page: int = Field(0, description="The page number for pagination.")
    limit: int = Field(10000, description="The number of results per page.")


class GetTargetCompoundInTargetCollectionQueryParams(BaseModel):
    target_compound_id: Optional[str] = Field(
        None,
        description="The target compound ID filter for which you want to fetch the assosiated target collections ids.",
    )
    target_collection_id: Optional[str] = Field(
        None,
        description="The target collection ID filter for which you want to fetch the assosiated target compound ids.",
    )
    sort: Optional[str] = Field(
        None,
        description="The column name by which you want to sort the results. The column name should be either target_compound_id or target_collection_id.",
    )
    order: Optional[str] = Field(
        None,
        description="Can either be asc for ascending order or desc for descending order.",
    )
    page: int = Field(0, description="The page number for pagination, default 0")
    limit: int = Field(10000, description="The number of results per page.")
