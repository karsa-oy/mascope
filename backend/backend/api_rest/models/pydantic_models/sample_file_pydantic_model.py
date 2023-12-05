from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import timezone, datetime as dt


class SampleFileBase(BaseModel):
    filename: str = Field(..., description="Name of the sample file")
    instrument: Optional[str] = Field(
        ..., description="Instrument associated with the file"
    )
    datetime: Optional[dt] = Field(..., description="Datetime associated with the file")
    datetime_utc: Optional[dt] = Field(
        ..., description="UTC datetime associated with the file"
    )
    length: Optional[float] = Field(..., description="Length of the sample file")
    # range: Optional[Dict] = Field(..., description="Range of the sample file")
    range: Optional[List[float]] = Field(..., description="Range of the sample file")
    mz_calibration: Optional[Dict] = Field(
        ..., description="mz_calibration of the sample file"
    )
    tic: Optional[float] = Field(..., description="tic of the sample file")


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


class GetSampleFilePeakTimeseriesBody(BaseModel):
    peak_mz: float
    peak_mz_tolerance_ppm: Optional[float] = 1
