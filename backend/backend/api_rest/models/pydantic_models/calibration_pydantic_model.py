from pydantic import BaseModel, Field
from typing import Optional


class CalibrationMzFitParams(BaseModel):
    # TODO_configuration default values
    match_score_min: float = Field(0, description="Minimum match score")
    refine_window: int = Field(100, description="Refine window parameter")
    peak_intensity_min: float = Field(1000.0, description="Minimum peak intensity")
    isotope_abundance_min: float = Field(0.1, description="Minimum isotope abundance")


class CalibrationMzApplyData(BaseModel):
    fit: dict = Field(..., description="Fit parameteres")


class CalibrationMzCalibrateBatchBody(BaseModel):
    params: CalibrationMzFitParams = CalibrationMzFitParams()
    independent_transaction: Optional[bool] = Field(
        default=True,
        description="Flag indicating whether the calibration is an independent transaction and if the operation should emit a reload event for the sample batch, raise the error if called internally.",
    )
