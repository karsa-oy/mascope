"""
Acquisition dataset pydantic models for API validation and serialization.

Defines data models for acquisition dataset related requests and responses
"""

from pydantic import Field, field_validator

from mascope_backend.api.models.base_pydantic_model import QueryParamsModel


class GetAcquisitionDatasetQueryParams(QueryParamsModel):
    """
    Query parameters for filtering ACQUISITION dataset.

    This model defines the parameters that can be passed to the get_acquisition_dataset
    endpoint
    """

    instrument: str | None = Field(
        None,
        description="Filter by instrument associated with the acquisition dataset.",
    )

    @field_validator("instrument")
    @classmethod
    def validate_instrument(cls, instrument: str | None) -> str | None:
        """Validate instrument is not empty."""
        if instrument is not None and instrument.strip() == "":
            raise ValueError("Instrument cannot be empty or contain only whitespace")
        return instrument
