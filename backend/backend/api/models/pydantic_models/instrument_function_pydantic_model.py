from pydantic import BaseModel, Field, validator, root_validator, ValidationError
from typing import Optional


class GetInstrumentFunctionsQueryParams(BaseModel):
    instrument: Optional[str] = Field(None, description="Filter by instrument name.")
    sort: Optional[str] = Field(None, description="Field to sort by.")
    order: Optional[str] = Field(
        None, description="Order of sorting, can be either 'asc' or 'desc'."
    )
    page: int = Field(0, description="Page number for pagination.")
    limit: int = Field(10000, description="Number of items per page.")


class GetInstrumentFunctionQueryParams(BaseModel):
    filename: Optional[str] = Field(
        None,
        description="When filename is used, the endpoint returns the latest instrument function for the specified file's instrument, as of the file's creation date and time.",
    )
    instrument_function_id: Optional[str] = Field(
        None,
        description="If ID provided, the system directly retrieves the instrument function details associated with this ID.",
    )

    @root_validator
    def check_filename_or_instrument_function_id(cls, values):
        filename, instrument_function_id = values.get("filename"), values.get(
            "instrument_function_id"
        )
        if (filename and instrument_function_id) or (
            not filename and not instrument_function_id
        ):
            raise ValueError(
                "Must provide either 'filename' or 'instrument_function_id', not both."
            )
        return values
