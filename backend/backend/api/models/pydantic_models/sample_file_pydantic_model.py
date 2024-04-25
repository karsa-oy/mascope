from pydantic import BaseModel, Field, validator, ValidationError
from typing import Optional, Dict, List
from datetime import timezone, datetime as dt


class SampleFileBase(BaseModel):
    filename: str = Field(..., description="Name of the sample file")
    instrument: Optional[str] = Field(
        ..., description="Instrument associated with the file"
    )
    datetime: Optional[dt] = Field(
        ..., description="Datetime (local) of creation of the sample file"
    )
    datetime_utc: Optional[dt] = Field(
        ..., description="Datetime (UTC) of creation of the sample file"
    )
    length: Optional[float] = Field(..., description="Length of the sample file")
    range: Optional[List[float]] = Field(
        ..., description="m/z range of the sample file"
    )
    mz_calibration: Optional[Dict] = Field(
        ..., description="m/z calibration function parameters of the sample file"
    )
    tic: Optional[float] = Field(..., description="TIC of the sample file")
    polarity: Optional[str] = Field(..., description="Polarity of the sample file")


class SampleFileCreate(SampleFileBase):
    pass


class SampleFileUpdate(SampleFileBase):
    filename: Optional[str] = Field(None, description="Name of the sample file")


class SampleFileInDB(SampleFileBase):
    sample_file_id: str = Field(..., description="ID of the sample file")

    class Config:
        orm_mode = True
        # datetime and datetime_utc fields will be represented in the ISO 8601 format in response
        json_encoders = {
            dt: lambda v: v.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
        }


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
    t_min: float = Field(None, description="Start of the time range", ge=0)
    t_max: float = Field(None, description="End of the time range", gt=0)
    mz_min: float = Field(None, description="Start of the m/z range", ge=0)
    mz_max: float = Field(None, description="End of the m/z range", gt=0)

    @validator("t_max")
    def validate_time_range(cls, t_max, values):
        t_min = values.get("t_min")
        if t_min is not None and t_max is not None:
            if t_max <= t_min:
                raise ValueError("t_max must be greater than t_min")
        elif t_min is None and t_max is not None or t_min is not None and t_max is None:
            raise ValueError("Both t_min and t_max must be provided")
        return t_max

    @validator("mz_max")
    def validate_mz_range(cls, mz_max, values):
        mz_min = values.get("mz_min")
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
        return mz_max
