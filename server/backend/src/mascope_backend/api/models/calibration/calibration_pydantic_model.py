from typing import Optional
from pydantic import BaseModel, Field, model_validator
from mascope_backend.api.models.base_pydantic_model import QueryParamsModel


# TODO_configuration default calibration parameters
DEFAULT_MATCH_SCORE_MIN = 0.0
DEFAULT_REFINE_WINDOW = 100
DEFAULT_PEAK_INTENSITY_MIN = 1000.0
DEFAULT_ISOTOPE_ABUNDANCE_MIN = 0.1


class GetMzCalibrationQueryParams(QueryParamsModel):
    sample_item_id: Optional[str] = Field(
        None,
        description="Filter by the sample item ID for which you want to fetch m/z calibration.",
    )
    instrument: Optional[str] = Field(
        None,
        description="The instrument name to query for the last m/z calibration of that instrument.",
    )

    @model_validator(mode="after")
    @classmethod
    def check_sample_item_id_or_instrument(cls, values):
        sample_item_id, instrument = values.sample_item_id, values.instrument
        if not sample_item_id and not instrument:
            raise ValueError(
                "Please specify a sample item ID or an instrument name to search for m/z calibration."
            )
        if sample_item_id and instrument:
            raise ValueError(
                "Please specify only one: either a sample item ID or an instrument name, not both."
            )
        return values


class MzCalibrationParams(BaseModel):
    match_score_min: float = Field(
        DEFAULT_MATCH_SCORE_MIN, description="Minimum match score"
    )
    refine_window: int = Field(
        DEFAULT_REFINE_WINDOW, description="Refine window parameter"
    )
    peak_intensity_min: float = Field(
        DEFAULT_PEAK_INTENSITY_MIN, description="Minimum peak intensity"
    )
    isotope_abundance_min: float = Field(
        DEFAULT_ISOTOPE_ABUNDANCE_MIN, description="Minimum isotope abundance"
    )


class CalibrationMzApplyBody(BaseModel):
    fit: dict = Field(..., description="Fit parameteres")
