"""Request and response schemas for the peak assignments API."""

from datetime import datetime

from pydantic import BaseModel, Field

from mascope_backend.api.new.peak_assignments.config import PeakAssignmentConfig


class PeakAssignmentRunRecord(BaseModel):
    """One peak assignment run over a sample."""

    peak_assignment_run_id: str
    sample_item_id: str
    engine_version: str
    status: str
    config: dict | None = None
    error: str | None = None
    peak_assignment_run_utc_created: datetime | None = None
    peak_assignment_run_utc_completed: datetime | None = None


class PeakAssignmentRecord(BaseModel):
    """One observed peak with its committed assignment."""

    peak_assignment_id: str
    peak_assignment_run_id: str
    sample_item_id: str
    sample_peak_id: str
    sample_peak_mz: float
    sample_peak_intensity: float
    sample_peak_tof: float | None = None
    role: str
    assigned_formula: str | None = None
    ion_formula: str | None = None
    ionization_mechanism_id: str | None = None
    isotope_label: str | None = None
    source: str | None = None
    match_score: float | None = None
    mz_error_ppm: float | None = None
    abundance_error: float | None = None
    tier: str
    target_compound_id: str | None = None
    target_ion_id: str | None = None
    owner_peak_assignment_id: str | None = None
    alternatives: list | None = None
    provenance: dict | None = None


class PeakAssignmentsResponse(BaseModel):
    """Peaks-with-assignments for a sample and the run they belong to."""

    status: str = "success"
    message: str
    results: int
    run: PeakAssignmentRunRecord | None = None
    data: list[PeakAssignmentRecord]


class PeakAssignmentRunsResponse(BaseModel):
    """Peak assignment runs of a sample, newest first."""

    status: str = "success"
    message: str
    results: int
    data: list[PeakAssignmentRunRecord]


class PeakAssignmentQueryParams(BaseModel):
    """Optional filters for the peaks-with-assignments query."""

    peak_assignment_run_id: str | None = Field(
        None, description="Specific run to read; defaults to the latest completed run."
    )
    tier: str | None = Field(
        None,
        description=(
            "Filter by confidence tier: identified, candidate, "
            "below_assignability, or unassigned."
        ),
    )
    role: str | None = Field(
        None,
        description=(
            "Filter by peak role: M0, iso_child, reagent, artifact, or unassigned."
        ),
    )
    source: str | None = Field(
        None, description="Filter by assignment source: database or untargeted."
    )


class AssignSamplePeaksBody(BaseModel):
    """Request body for launching a peak assignment run."""

    config: PeakAssignmentConfig | None = Field(
        None,
        description=(
            "Optional run configuration; engine defaults are used when omitted."
        ),
    )
