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

    instrument: str = Field(
        ...,
        description="Instrument associated with the acquisition dataset.",
    )
    year: int | None = Field(
        None,
        description="Calendar year for the acquisition dataset. Defaults to current year.",
    )

    @field_validator("instrument")
    @classmethod
    def validate_instrument(cls, instrument: str) -> str:
        """Validate instrument is not empty."""
        if instrument.strip() == "":
            raise ValueError("Instrument cannot be empty or contain only whitespace")
        return instrument
