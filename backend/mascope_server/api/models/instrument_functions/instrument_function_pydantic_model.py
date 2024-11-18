from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, model_validator, field_validator
from mascope_server.api.models.base_pydantic_model import QueryParamsModel

from mascope_server.api.new.instrument_functions.params import InstrumentFunctionParams


instrument_function_params = InstrumentFunctionParams()


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


class GetMethodFilesQueryParams(QueryParamsModel):
    filename: str = Field(..., description="The filename to get method files by")


class PeakShape(BaseModel):
    x: List[float] = Field(
        ...,
        description="X-axis values representing the mass-to-charge ratio (m/z) for the peak shape.",
    )
    y: List[float] = Field(
        ...,
        description="Y-axis values representing intensity for each corresponding m/z value in the peak shape.",
    )


class InstrumentFunctionBase(BaseModel):
    instrument: str = Field(..., description="Instrument name")
    datetime_utc: datetime = Field(
        ...,
        description="UTC timestamp from which onwards the specified instrument functions are applied, until new instrument functions are generated.",
    )
    peakshape: PeakShape = Field(..., description="Peak shape data")
    resolution_function: List[float] = Field(
        ...,
        description="Parameters defining the resolution function, which is used to scale the width of peaks accurately during peak fitting.",
    )


class InstrumentFunctionCreateBody(InstrumentFunctionBase):
    method_file: str = Field(
        ...,
        description="Name of the method file associated with the instrument function. Must start with the date in YYYYMMDD format.",
    )


class InstrumentFunctionFitParams(BaseModel):
    threshold: float = Field(
        default=instrument_function_params.threshold,
        description="R-squared threshold filtering non-(skewed) Gaussian peaks from instrument function evaluation",
    )

    @field_validator("threshold")
    @classmethod
    def validate_threshold(cls, v):
        if not 0 <= v < 1:
            raise ValueError(
                "R-squared threshold must be between 0 and 1, inclusive of 0."
            )
        return v


class FitInstrumentFunctionsBody(BaseModel):
    filename: str = Field(..., description="The filename of the file used for the fit")
    instrument_function_params: InstrumentFunctionFitParams = Field(
        InstrumentFunctionFitParams(),
        description="The instrument function fitting parameters",
    )


class ProcessInstrumentFunctionBody(BaseModel):
    filename: str = Field(
        ..., description="Filename to process instrument functions for"
    )
    existing_method_file: Optional[str] = Field(
        None, description="An existing method file to use for this sample"
    )
    new_method_file: Optional[str] = Field(
        None, description="A new method file to create and use for this sample"
    )
    new_instrument_function: Optional[InstrumentFunctionBase] = Field(
        None,
        description="Instrument functions to create and associate with the sample file",
    )

    @model_validator(mode="after")
    @classmethod
    def validate_method_file_fields(cls, values):
        if values.existing_method_file and values.new_method_file:
            raise ValueError(
                f"Process instrument function ({values.sample_item.filename}): expecting either an existing_method_file argument or a new_method_file_argument but not both."
            )
        return values
