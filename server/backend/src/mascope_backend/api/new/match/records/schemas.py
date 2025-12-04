"""
Match records pydantic models for API validation and serialization.

Defines data models for match records related requests and responses
with validation rules and business logic constraints.
"""

from pydantic import BaseModel, Field, model_validator
from mascope_backend.api.models.base_pydantic_model import (
    QueryParamsModel,
    RequestBodyModel,
)


class MatchRecordsQueryParams(QueryParamsModel):
    """Query parameters for match records endpoint"""

    sample_item_id: str | None = Field(
        None, description="Sample item ID for sample-level match records"
    )
    sample_batch_id: str | None = Field(
        None, description="Sample batch ID for batch-level match records"
    )

    @model_validator(mode="after")
    @classmethod
    def validate_sample_filter(cls, values):
        """Validate that sample_item_id or sample_batch_id is provided"""
        sample_item_id, sample_batch_id = values.sample_item_id, values.sample_batch_id

        if not sample_item_id and not sample_batch_id:
            raise ValueError(
                "Please specify either sample_item_id or sample_batch_id to retrieve match records."
            )

        if sample_item_id and sample_batch_id:
            raise ValueError(
                "Please specify only one: either a sample item ID or a sample batch ID, not both."
            )

        return values


class MatchIonRecordsBody(RequestBodyModel):
    """Query parameters for match ion records endpoint"""

    sample_item_ids: list[str] | None = Field(
        None, description="Sample item IDs for sample-level match records"
    )
    sample_batch_id: str | None = Field(
        None, description="Sample batch ID for batch-level match records"
    )
    target_collection_id: str | None = Field(
        None, description="Optional filter by specific target collection"
    )
    target_ion_ids: list[str] | None = Field(
        None, description="Optional filter by specific target ions"
    )

    @model_validator(mode="after")
    @classmethod
    def validate_sample_filter(cls, values):
        """Validate that sample_item_id or sample_batch_id is provided"""
        sample_item_ids, sample_batch_id = (
            values.sample_item_ids,
            values.sample_batch_id,
        )

        if not sample_item_ids and not sample_batch_id:
            raise ValueError(
                "Please specify either sample_item_ids or sample_batch_id to retrieve match records."
            )

        if sample_item_ids and sample_batch_id:
            raise ValueError(
                "Please specify only one: either a sample item ID or a sample batch ID, not both."
            )

        if sample_item_ids and len(sample_item_ids) == 0:
            raise ValueError("sample_item_ids list cannot be empty if provided.")

        return values

    @model_validator(mode="after")
    @classmethod
    def validate_target_filter(cls, values):
        """Validate that only one of target_collection_id and target_ion_id is provided"""
        target_collection_id, target_ion_ids = (
            values.target_collection_id,
            values.target_ion_ids,
        )

        if target_collection_id and target_ion_ids:
            raise ValueError(
                "Please specify only one: either a target collection ID or a target ion ID, not both."
            )

        return values


class MatchIsotopeRecordsQueryParams(MatchRecordsQueryParams):
    """Query parameters for match isotope records endpoint"""

    target_collection_id: str | None = Field(
        None, description="Optional filter by specific target collection"
    )
    target_ion_id: str | None = Field(
        None, description="Optional filter by specific target ion"
    )

    @model_validator(mode="after")
    @classmethod
    def validate_target_filter(cls, values):
        """Validate that only one of target_collection_id and target_ion_id is provided"""
        target_collection_id, target_ion_id = (
            values.target_collection_id,
            values.target_ion_id,
        )

        if target_collection_id and target_ion_id:
            raise ValueError(
                "Please specify only one: either a target collection ID or a target ion ID, not both."
            )

        return values


class MatchRecordsBatchOverviewQueryParams(QueryParamsModel):
    """Query parameters for match records endpoint"""

    sample_batch_id: str = Field(
        ..., description="Sample batch ID for batch-level match records"
    )
    target_collection_id: str = Field(
        ..., description="Filter by specific target collection"
    )


class MatchRecordsResponse(BaseModel):
    """Response model for match records"""

    status: str = Field(description="Response status")
    message: str = Field(description="Response message")
    results: int = Field(description="Total number of results")
    data: list[dict] = Field(description="Match records data")


class MatchRecordsSingleResponse(BaseModel):
    """Response model for single match record"""

    status: str = Field(description="Response status")
    message: str = Field(description="Response message")
    data: dict = Field(description="Single match record data")
