from pydantic import BaseModel, Field, model_validator
from typing import Optional


class GetMzCalibrationQueryParams(BaseModel):
    sample_item_id: Optional[str] = Field(
        None,
        description="Filter by the sample item ID for which you want to fetch m/z calibration.",
    )
    instrument: Optional[str] = Field(
        None,
        description="The instrument name to query for the last m/z calibration of that instrument.",
    )

    @model_validator(mode='after')
    def check_sample_item_id_or_instrument(cls, values):
        sample_item_id, instrument = values.sample_item_id, values.instrument
        if (sample_item_id and instrument) or (not sample_item_id and not instrument):
            raise ValueError(
                "Must provide either ID of the sample or instrument name, not both."
            )
        return values


class CalibrationMzFitParams(BaseModel):
    # TODO_configuration default values
    match_score_min: float = Field(0, description="Minimum match score")
    refine_window: int = Field(100, description="Refine window parameter")
    # TODO check the default peak_intensity_min
    peak_intensity_min: float = Field(1000.0, description="Minimum peak intensity")
    isotope_abundance_min: float = Field(0.1, description="Minimum isotope abundance")


class CalibrationMzApplyBody(BaseModel):
    fit: dict = Field(..., description="Fit parameteres")
