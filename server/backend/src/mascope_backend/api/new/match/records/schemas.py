"""
Match records pydantic models for API validation and serialization.

Defines data models for match records related requests and responses
with validation rules and business logic constraints.
"""

from pydantic import BaseModel, Field, model_validator
from mascope_backend.api.models.base_pydantic_model import QueryParamsModel


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
    def validate_request_params(cls, values):
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


class MatchIonRecordsQueryParams(MatchRecordsQueryParams):
    """Query parameters for match ion records endpoint"""

    target_collection_id: str | None = Field(
        None, description="Optional filter by specific target collection"
    )


class MatchIsotopeRecordsQueryParams(MatchIonRecordsQueryParams):
    """Query parameters for match isotope records endpoint"""

    target_ion_id: str | None = Field(
        None, description="Optional filter by specific target ion"
    )


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
