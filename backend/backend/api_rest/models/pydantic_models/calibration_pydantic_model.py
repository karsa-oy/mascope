from pydantic import BaseModel, Field
from typing import List


class CalibrationMzFitParams(BaseModel):
    # TODO_configuration default values
    match_score_min: float = Field(0, description="Minimum match score")
    refine_window: int = Field(100, description="Refine window parameter")
    peak_intensity_min: float = Field(1000.0, description="Minimum peak intensity")
    isotope_abundance_min: float = Field(0.1, description="Minimum isotope abundance")


class CalibrationMzApplyData(BaseModel):
    fit: dict = Field(..., description="Fit parameteres")


class CalibrationMzCalibrateBatchData(BaseModel):
    sample_batch: dict
    sample_items: List[dict]
    params: CalibrationMzFitParams = CalibrationMzFitParams()
