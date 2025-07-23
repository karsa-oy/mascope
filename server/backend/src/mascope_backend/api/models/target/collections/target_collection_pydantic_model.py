"""
Target collection pydantic models for API validation and serialization.

Defines data models for target collection related requests and responses
with validation rules and business logic constraints.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from mascope_backend.api.models.target.collections.config import (
    target_collection_config,
)
from mascope_backend.api.models.target.compounds.target_compound_pydantic_model import (
    TargetCompoundBase,
)
from mascope_backend.api.models.base_pydantic_model import QueryParamsModel


class TargetCollectionBaseValidator:
    """Base validation logic for target collection shared fields."""

    @field_validator("target_collection_name")
    @classmethod
    def validate_target_collection_name(cls, name: str | None) -> str | None:
        """Validate target collection name is not empty or whitespace."""
        if name is not None and name.strip() == "":
            raise ValueError(
                "Target collection name cannot be empty or contain only whitespace."
            )
        return name

    @field_validator("target_collection_type")
    @classmethod
    def validate_target_collection_type(cls, tc_type: str | None) -> str | None:
        """Validate target collection type."""
        if tc_type and tc_type not in target_collection_config.TARGET_COLLECTION_TYPES:
            allowed_types = ", ".join(target_collection_config.TARGET_COLLECTION_TYPES)
            raise ValueError(
                f"Invalid target collection type. Must be one of: {allowed_types}"
            )
        return tc_type




class TargetCollectionBase(BaseModel):
    """Base model with common fields for TargetCollection."""

    target_collection_name: str = Field(
        ..., description="Name of the target collection"
    )
    target_collection_description: str | None = Field(
        "", description="Description of the target collection"
    )
    target_collection_type: str = Field(
        default=target_collection_config.DEFAULT_TARGET_COLLECTION_TYPE,
        description="Type of the target collection",
    )

    model_config = ConfigDict(from_attributes=True)


class TargetCollectionCreate(TargetCollectionValidator, TargetCollectionBase):
    """Model used for target collection creation requests."""

    target_compounds_create: list[TargetCompoundBase] | None = Field(
        None, description="Compounds to be created and added to the target collection"
    )
    target_compound_ids: list[str] | None = Field(
        None,
        description="IDs of already existing in DB target compounds to be associated with the target collection",
    )
    sample_batch_ids: list[str] | None = Field(
        None, description="IDs of sample batches where to add the new target collection"
    )

    @model_validator(mode="after")
    @classmethod
    def validate_at_least_one_compound_provided(cls, values):
        """Validate at least one compound is provided."""
        compounds_create = values.target_compounds_create
        compound_ids = values.target_compound_ids

        if not compounds_create and not compound_ids:
            raise ValueError("At least one compound must be provided.")
        return values


class TargetCollectionUpdate(TargetCollectionValidator, TargetCollectionBase):
    """Model used for target collection update requests."""

    target_compound_ids: list[str] | None = Field(
        None,
        description="IDs of already existing in db target compounds to be associated with the target collection",
    )
    target_compounds_create: list[TargetCompoundBase] | None = Field(
        None, description="Compounds to be created and added to the target collection"
    )
    sample_batch_ids: list[str] | None = Field(
        None, description="IDs of sample batches associated with the target collection"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_compounds_or_batches(cls, values):
        """Validate compounds or batches update logic."""
        compounds_create = values.get("target_compounds_create")
        compound_ids = values.get("target_compound_ids")
        batches = values.get("sample_batch_ids")

        # When updating batches, ensure no compounds are provided
        if batches is not None and (compounds_create or compound_ids):
            raise ValueError(
                "You cannot update target compounds while simultaneously updating sample batch associations."
            )

        # When not updating batches, ensure at least one compound is provided
        if batches is None:
            if not compounds_create and not compound_ids:
                raise ValueError(
                    "At least one compound (to create or associate) must be provided when not updating sample batch associations."
                )

        return values


class GetTargetCollectionsQueryParams(QueryParamsModel):
    target_collection_type: Optional[str] = Field(
        None,
        description="The target collection type for which you want to fetch the target collections.",
    )
    target_collection_name: Optional[str] = Field(
        None,
        description="The name of the target collection for which you want to fetch the target collections.",
    )
    sample_batch_id: Optional[str] = Field(
        None, description="The ID of the sample batch to filter collections by."
    )
    sort: Optional[str] = Field(
        None,
        description="The column name by which you want to sort the results. The column name should be one of the fields of target_collection.",
    )
    order: Optional[str] = Field(
        None,
        description="Can either be asc for ascending order or desc for descending order.",
    )
    page: int = Field(0, description="The page number for pagination, default 0")
    limit: int = Field(10000, description="The number of results per page.")


class GetTargetCollectionsInSampleBatchQueryParams(QueryParamsModel):
    sample_batch_id: Optional[str] = Field(
        None,
        description="The sample batch ID filter for which you want to fetch the assosiated target collections ids.",
    )
    target_collection_id: Optional[str] = Field(
        None,
        description="The target collection ID filter for which you want to fetch the assosiated sample batches ids.",
    )
    sort: Optional[str] = Field(
        None,
        description="The column name by which you want to sort the results. The column name should be either sample_batch_id or target_collection_id.",
    )
    order: Optional[str] = Field(
        None,
        description="Can either be asc for ascending order or desc for descending order.",
    )
    page: int = Field(0, description="The page number for pagination, default 0")
    limit: int = Field(10000, description="The number of results per page.")
