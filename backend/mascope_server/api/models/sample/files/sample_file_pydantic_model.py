from typing import Optional, Dict, List, Annotated
from datetime import datetime as dt
from pydantic import BaseModel, Field, field_validator, model_validator


class SampleFileBase(BaseModel):
    filename: str = Field(..., description="Name of the sample file")
    instrument: str = Field(..., description="Instrument associated with the file")
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
    datetime: dt = Field(
        ..., description="Datetime (local) of creation of the sample file"
    )
    datetime_utc: dt = Field(
        ..., description="Datetime (UTC) of creation of the sample file"
    )
    length: float = Field(..., description="Length of the sample file")
    range: List[float] = Field(..., description="m/z range of the sample file")
    mz_calibration: Dict = Field(
        ..., description="m/z calibration function parameters of the sample file"
    )
    tic: float = Field(..., description="TIC of the sample file")
    polarity: str = Field("", description="Polarity of the sample file")


class GetSampleFilesQueryParams(BaseModel):
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


class GetSampleFilePeakTimeseriesBody(BaseModel):
    peak_mz: float
    peak_mz_tolerance_ppm: Optional[float] = 1


class GetSpectrumQueryParams(BaseModel):
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
