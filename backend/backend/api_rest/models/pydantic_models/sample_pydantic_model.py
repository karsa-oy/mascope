from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class FilterParams(BaseModel):
    mz_tolerance: float
    isotope_ratio_tolerance: float
    peak_min_intensity: float
    min_isotope_abundance: float
    min_isotope_correlation: float


class MatchFilterBody(BaseModel):
    batch_id: str
    filter_params: FilterParams


class GetSamplesBody(BaseModel):
    sample_item_id: Optional[str] = None
    sample_item_id_active: Optional[str] = None
    sample_file_id: Optional[str] = None
    sample_batch_id: Optional[str] = None
    filename: Optional[str] = None
    instrument: Optional[str] = None
    sample_item_type: Optional[str] = None
    minDatetime: Optional[datetime] = None
    maxDatetime: Optional[datetime] = None
    sort: Optional[str] = None
    order: Optional[str] = None
    filter_params: Optional[FilterParams] = None
    page: Optional[int] = 0
    limit: Optional[int] = 10000
