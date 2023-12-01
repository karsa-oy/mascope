from pydantic import BaseModel
from typing import Optional


class GetPeakTimeseriesBody(BaseModel):
    filename: str
    peak_mz: float
    peak_mz_tolerance_ppm: Optional[float] = 1
