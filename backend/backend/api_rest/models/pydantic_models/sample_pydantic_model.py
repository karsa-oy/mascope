from typing import Optional
from pydantic import BaseModel


class FilterParams(BaseModel):
    mz_tolerance: float
    isotope_ratio_tolerance: float
    peak_min_intensity: float = 0.0
    min_isotope_abundance: float
    min_isotope_correlation: float


class MatchFilterBody(BaseModel):
    batch_id: str
    filter_params: FilterParams


class LoadSamplesBody(BaseModel):
    batch_id: str
    sample_item_active_id: str
    filter_params: FilterParams
