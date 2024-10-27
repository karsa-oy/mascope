import re
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
from mascope_server.api.models.base_pydantic_model import QueryParamsModel


class GetInstrumentFunctionsQueryParams(QueryParamsModel):
    instrument: Optional[str] = Field(None, description="Filter by instrument name.")
    method_file: Optional[str] = Field(None, description="Filter by method file name.")
    sort: Optional[str] = Field(None, description="Field to sort by.")
    order: Optional[str] = Field(
        None, description="Order of sorting, can be either 'asc' or 'desc'."
    )
    page: int = Field(0, description="Page number for pagination.")
    limit: int = Field(10000, description="Number of items per page.")


class GetInstrumentFunctionQueryParams(QueryParamsModel):
    filename: Optional[str] = Field(
        None,
        description="When filename is used, the endpoint returns the latest instrument function for the specified file's instrument, as of the file's creation date and time.",
    )
    instrument_function_id: Optional[str] = Field(
        None,
        description="If ID provided, the system directly retrieves the instrument function details associated with this ID.",
    )

    @model_validator(mode="after")
    @classmethod
    def check_filename_or_instrument_function_id(cls, values):
        filename, instrument_function_id = (
            values.filename,
            values.instrument_function_id,
        )
        if (filename and instrument_function_id) or (
            not filename and not instrument_function_id
        ):
            raise ValueError(
                "Must provide either 'filename' or 'instrument_function_id', not both."
            )
        return values


class PeakShape(BaseModel):
    x: List[float] = Field(
        ...,
        description="X-axis values representing the mass-to-charge ratio (m/z) for the peak shape.",
    )
    y: List[float] = Field(
        ...,
        description="Y-axis values representing intensity for each corresponding m/z value in the peak shape.",
    )


class InstrumentFunctionCreateBody(BaseModel):
    instrument: str = Field(..., description="Instrument name")
    method_file: str = Field(
        ...,
        description="Name of the method file associated with the instrument function. Must start with the date in YYYYMMDD format.",
    )
    datetime_utc: datetime = Field(
        ...,
        description="UTC timestamp from which onwards the specified instrument functions are applied, until new instrument functions are generated.",
    )
    peakshape: PeakShape = Field(..., description="Peak shape data")
    resolution_function: List[float] = Field(
        ...,
        description="Parameters defining the resolution function, which is used to scale the width of peaks accurately during peak fitting.",
    )

    @field_validator("method_file")
    @classmethod
    def validate_method_file(cls, value):
        # Ensure that the method_file starts with exactly 8 digits
        if not re.match(r"^\d{8}", value):
            raise ValueError(
                "The method_file must start with a date in YYYYMMDD format (e.g., '20240528')."
            )

        # Extract first 8 digits and check if it forms a valid date
        date_part = value[:8]
        try:
            datetime.strptime(date_part, "%Y%m%d")
        except ValueError as e:
            raise ValueError(
                "The method_file must start with a valid date in YYYYMMDD format (e.g., '20240528')."
            ) from e

        return value
