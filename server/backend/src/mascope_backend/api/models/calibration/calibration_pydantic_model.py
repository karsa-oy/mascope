from pydantic import BaseModel, Field, model_validator
from mascope_backend.api.models.base_pydantic_model import QueryParamsModel
from mascope_backend.api.models.calibration.config import calibration_config


class GetMzCalibrationQueryParams(QueryParamsModel):
    sample_item_id: str | None = Field(
        None,
        description="Filter by the sample item ID for which you want to fetch m/z calibration.",
    )
    instrument: str | None = Field(
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
    refine_window: int = Field(..., description="Refine window parameter")
    match_score_min: float = Field(
        calibration_config.DEFAULT_MATCH_SCORE_MIN, description="Minimum match score"
    )
    peak_intensity_min: float = Field(
        calibration_config.DEFAULT_PEAK_INTENSITY_MIN,
        description="Minimum peak intensity",
    )
    isotope_abundance_min: float = Field(
        calibration_config.DEFAULT_ISOTOPE_ABUNDANCE_MIN,
        description="Minimum isotope abundance",
    )


class OrbiCalibrationParams(MzCalibrationParams):
    refine_window: int = Field(
        calibration_config.ORBI_DEFAULT_REFINE_WINDOW,
        description="Refine window parameter",
    )


class TofCalibrationParams(MzCalibrationParams):
    refine_window: int = Field(
        calibration_config.TOF_DEFAULT_REFINE_WINDOW,
        description="Refine window parameter",
    )


class CalibrationFitParams(MzCalibrationParams):
    mz_error_tolerance: float = Field(..., description="m/z error tolerance")
    tic_threshold: float = Field(
        calibration_config.TIC_THRESHOLD, description="TIC threshold"
    )
    calibration_collection_id: str | None = Field(
        None, description="Calibration collection ID"
    )
    ionization_mechanism_ids: list[str | None] = Field(
        None, description="Ionization mechanism IDs"
    )


class TofCalibrationFitParams(CalibrationFitParams):
    mz_error_tolerance: float = Field(
        calibration_config.TOF_MZ_ERROR_TOLERANCE, description="m/z error tolerance"
    )


class OrbiCalibrationFitParams(CalibrationFitParams):
    mz_error_tolerance: float = Field(
        calibration_config.ORBI_MZ_ERROR_TOLERANCE, description="m/z error tolerance"
    )


class CalibrationMzApplyBody(BaseModel):
    fit: dict = Field(..., description="Fit parameters")
