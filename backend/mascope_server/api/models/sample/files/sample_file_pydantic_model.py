from typing import Optional, Dict, List, Annotated, Literal
from datetime import datetime as dt
from pydantic import BaseModel, Field, field_validator, model_validator
from fastapi import UploadFile
from fastapi.exceptions import RequestValidationError
from mascope_server.api.models.base_pydantic_model import QueryParamsModel

# TODO_configuration Default sample file upload params
FILE_UPLOAD_EXTENSIONS = {".h5", ".raw"}
FILE_UPLOAD_SIZE_LIMIT = 200 * 1024 * 1024  # 200 MB


class SampleFileBase(BaseModel):
    filename: str = Field(..., description="Name of the sample file")
    instrument: str = Field(..., description="Instrument associated with the file")
    method_file: Optional[str] = Field(None, description="Instrument config name")
    datetime: dt = Field(
        ..., description="Datetime (local) of creation of the sample file"
    )
    datetime_utc: dt = Field(
        ..., description="Datetime (UTC) of creation of the sample file"
    )
    length: float = Field(..., description="Length of the sample file")
    range: List[float] = Field(..., description="m/z range of the sample file")
    mz_calibration: Optional[Dict] = Field(
        None, description="m/z calibration function parameters of the sample file"
    )
    tic: float = Field(..., description="TIC of the sample file")
    polarity: str = Field(..., description="Polarity of the sample file")

    @field_validator("polarity")
    @classmethod
    def validate_polarity(cls, v):
        if v not in ["+", "-"]:
            raise ValueError("Polarity must be '+' or '-'")
        return v


class SampleFileCreate(SampleFileBase):
    pass


class SampleFileUpdate(BaseModel):
    filename: str = Field(..., description="Name of the sample file")
    instrument: str = Field(..., description="Instrument associated with the file")
    method_file: Optional[str] = Field(
        None, description="The instrument config name associated with the file"
    )
    instrument_function_id: Optional[str] = Field(
        None, description="The ID of the instrument function associated with the file"
    )
    datetime: dt = Field(
        ..., description="Datetime (local) of creation of the sample file"
    )
    datetime_utc: dt = Field(
        ..., description="Datetime (UTC) of creation of the sample file"
    )
    length: float = Field(..., description="Length of the sample file")
    range: List[float] = Field(..., description="m/z range of the sample file")
    mz_calibration: Optional[Dict] = Field(
        None, description="m/z calibration function parameters of the sample file"
    )
    tic: float = Field(..., description="TIC of the sample file")
    polarity: str = Field("", description="Polarity of the sample file")


class SampleFileUpload(BaseModel):
    file: UploadFile = Field(..., description="The uploaded file")

    @field_validator("file")
    @classmethod
    def validate_extension(cls, file: UploadFile):
        if not any(file.filename.endswith(ext) for ext in FILE_UPLOAD_EXTENSIONS):
            # Raise a RequestValidationError directly
            raise RequestValidationError(
                [
                    {
                        "loc": ("file",),
                        "msg": f"Invalid file extension, allowed extensions: {', '.join(FILE_UPLOAD_EXTENSIONS)}",
                        "type": "value_error.file_extension",
                    }
                ]
            )
        return file

    @field_validator("file")
    @classmethod
    def validate_size(cls, file: UploadFile):
        if hasattr(file, "size") and file.size > FILE_UPLOAD_SIZE_LIMIT:
            size_limit_mb = FILE_UPLOAD_SIZE_LIMIT / 1024 / 1024
            # Raise a RequestValidationError directly
            raise RequestValidationError(
                [
                    {
                        "loc": ("file",),
                        "msg": f"File exceeds the size limit of {size_limit_mb} MB.",
                        "type": "value_error.file_size",
                    }
                ]
            )
        return file


class GetSampleFilesQueryParams(QueryParamsModel):
    datetime_min: Optional[dt] = Field(None, description="Minimum datetime filter")
    datetime_max: Optional[dt] = Field(None, description="Maximum datetime filter")
    instrument: Optional[str] = Field(None, description="Filter by instrument")
    filename: Optional[str] = Field(None, description="Filter by filename")
    sort: Optional[str] = Field(
        "datetime_utc",
        description="The column name by which you want to sort the results.",
    )
    order: Optional[str] = Field(
        "asc",
        description="Can either be 'asc' for ascending order or 'desc' for descending order.",
    )
    page: int = Field(0, description="The page number for pagination, default 0")
    limit: int = Field(10000, description="The number of results per page.")


class GetRecentSampleFilesQueryParams(GetSampleFilesQueryParams):
    days: int = Field(
        1, description="Number of days to look back from current datetime"
    )


class GetSampleFilePeaksQueryParams(QueryParamsModel):
    areas: bool = Field(
        True,
        description="Include peak areas in the response. Represents the integrated area under the curve for each peak, reflecting the total intensity over time.",
    )
    heights: bool = Field(
        True,
        description="Include peak heights in the response. Represents the maximum intensity at the apex of each peak, showing the peak's highest intensity value.",
    )

    @model_validator(mode="after")
    @classmethod
    def validate_peak_variables(cls, values):
        if not values.areas and not values.heights:
            raise ValueError(
                "You need to request either peak areas, peak heights, or both. At least one of 'areas' or 'heights' must be set to True. "
            )
        return values


class ComputeAllSampleFilePeaksQueryParams(QueryParamsModel):
    if_exists: Literal["append", "replace"] = Field(
        "append",
        description="Whether to append to or replace any existing peaks in the sample file.",
    )


class GetSampleFilePeakTimeseriesBody(BaseModel):
    peak_mz: float
    peak_mz_tolerance_ppm: Optional[float] = 1


class GetSpectrumQueryParams(QueryParamsModel):
    t_min: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Start of the time range"
    )
    t_max: Optional[Annotated[float, Field(gt=0)]] = Field(
        None, description="End of the time range"
    )
    mz_min: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Start of the m/z range"
    )
    mz_max: Optional[Annotated[float, Field(gt=0)]] = Field(
        None, description="End of the m/z range"
    )

    @model_validator(mode="after")
    @classmethod
    def validate_time_range(cls, values):
        t_min = values.t_min
        t_max = values.t_max
        if t_min is not None and t_max is not None:
            if t_max <= t_min:
                raise ValueError("t_max must be greater than t_min")
        elif t_min is None and t_max is not None or t_min is not None and t_max is None:
            raise ValueError("Both t_min and t_max must be provided")
        return values

    @model_validator(mode="after")
    @classmethod
    def validate_mz_range(cls, values):
        mz_min = values.mz_min
        mz_max = values.mz_max
        if mz_min is not None and mz_max is not None:
            if mz_max <= mz_min:
                raise ValueError("mz_max must be greater than mz_min")
        elif (
            mz_min is None
            and mz_max is not None
            or mz_min is not None
            and mz_max is None
        ):
            raise ValueError("Both mz_min and mz_max must be provided")
        return values
