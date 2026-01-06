"""
Acquisition workspace pydantic models for API validation and serialization.

Defines data models for acquisition workspace related requests and responses
"""

from pydantic import Field, field_validator

from mascope_backend.api.models.base_pydantic_model import QueryParamsModel


class GetAcquisitionWorkspaceQueryParams(QueryParamsModel):
    """
    Query parameters for filtering ACQUISITION workspace.

    This model defines the parameters that can be passed to the get_acquisition_workspace endpoint
    """

    instrument: str | None = Field(
        None,
        description="Filter by instrument associated with the acquisition workspace.",
    )

    @field_validator("instrument")
    @classmethod
    def validate_instrument(cls, instrument: str | None) -> str | None:
        """Validate instrument is not empty."""
        if instrument is not None and instrument.strip() == "":
            raise ValueError("Instrument cannot be empty or contain only whitespace")
        return instrument
