"""Configuration for the peak-centric assignment engine."""

from pydantic import BaseModel, Field

from mascope_backend.api.new.cheminfo.config import cheminfo_config


# Bump when the assignment algorithm changes in a way that affects results.
# Stored on every PeakAssignmentRun so runs stay reproducible and comparable.
PEAK_ASSIGNMENT_ENGINE_VERSION = "0.1.0"


class PeakAssignmentConfig(BaseModel):
    """User-tunable configuration for one peak assignment run.

    The full (resolved) configuration is persisted on the PeakAssignmentRun
    row, together with the engine version.
    """

    run_untargeted: bool = Field(
        True,
        description=(
            "Run Stage B (untargeted composition search) for peaks that the "
            "database stage left unassigned."
        ),
    )
    mz_precision_ppm: float = Field(
        cheminfo_config.DEFAULT_MZ_PRECISION,
        description="m/z tolerance in ppm for the untargeted composition search.",
    )
    formula_ranges: str = Field(
        cheminfo_config.DEFAULT_FORMULA_RANGE,
        description="Element count ranges permitted in untargeted candidates.",
    )
    max_untargeted_peaks: int = Field(
        300,
        gt=0,
        description=(
            "Upper bound on the number of (most intense) unassigned peaks fed "
            "to the untargeted stage. Composition enumeration is the scaling "
            "risk; this bounds run time on dense spectra."
        ),
    )
    peak_intensity_threshold: float = Field(
        0.0,
        ge=0.0,
        description=(
            "Minimum peak intensity for a peak to enter the untargeted stage."
        ),
    )
    max_alternatives: int = Field(
        5,
        ge=0,
        description="Maximum number of runner-up candidates stored per peak.",
    )
