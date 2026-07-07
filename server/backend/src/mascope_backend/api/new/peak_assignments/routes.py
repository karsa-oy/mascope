"""
Peak assignments API routes.

Exposes the peak-centric assignment results ("every peak in a sample with its
formula and confidence") and the endpoint that launches an assignment run.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from mascope_backend.api.controllers.samples.lib.samples_fetch import fetch_sample
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.new.auth.dependencies import current_active_user
from mascope_backend.api.new.peak_assignments.schemas import (
    AssignSamplePeaksBody,
    PeakAssignmentQueryParams,
    PeakAssignmentRunsResponse,
    PeakAssignmentsResponse,
)
from mascope_backend.api.new.peak_assignments.service import (
    assign_sample_peaks,
    get_peak_assignment_runs,
    get_peak_assignments,
)
from mascope_backend.api.new.workspaces.dependencies import (
    check_sample_access,
    require_sample_role,
)
from mascope_backend.db import User
from mascope_backend.db.id import gen_id


peak_assignments_router = APIRouter(
    prefix="/api/peak-assignments", tags=["Peak Assignments"]
)


@peak_assignments_router.get(
    "/sample/{sample_item_id}", response_model=PeakAssignmentsResponse
)
@api_route(token_access=True)
async def get_peak_assignments_route(
    sample_item_id: str,
    query_params: PeakAssignmentQueryParams = Query(),
    user: User = Depends(current_active_user),
) -> PeakAssignmentsResponse:
    """
    Retrieve peaks-with-assignments for a sample.

    Returns one row per observed peak from the requested run (or the latest
    completed run), each carrying the committed formula, adduct, evidence,
    confidence tier, and optional reference to the curated target library.

    :param sample_item_id: The unique identifier of the sample.
    :param query_params: Optional run id and tier/role/source filters.
    :param user: The current authenticated user. Requires workspace guest role.
    :return: Run metadata and per-peak assignment records.
    """
    await check_sample_access(sample_item_id, user, "guest")
    result = await get_peak_assignments(
        sample_item_id=sample_item_id, **query_params.model_dump()
    )
    return PeakAssignmentsResponse.model_validate(result)


@peak_assignments_router.get(
    "/sample/{sample_item_id}/runs", response_model=PeakAssignmentRunsResponse
)
@api_route(token_access=True)
async def get_peak_assignment_runs_route(
    sample_item_id: str,
    user: User = Depends(current_active_user),
) -> PeakAssignmentRunsResponse:
    """
    Retrieve all peak assignment runs for a sample, newest first.

    :param sample_item_id: The unique identifier of the sample.
    :param user: The current authenticated user. Requires workspace guest role.
    :return: Run records with status, engine version, and configuration.
    """
    await check_sample_access(sample_item_id, user, "guest")
    result = await get_peak_assignment_runs(sample_item_id=sample_item_id)
    return PeakAssignmentRunsResponse.model_validate(result)


@peak_assignments_router.post("/sample/{sample_item_id}/assign")
@api_route(status_code=202, token_access=True)
async def assign_sample_peaks_route(
    sample_item_id: str,
    background_tasks: BackgroundTasks,
    body: AssignSamplePeaksBody | None = None,
    user: User = Depends(current_active_user),
    membership=Depends(require_sample_role("editor")),
) -> dict:
    """
    Launch a peak assignment run for a sample.

    Assigns a composition to every observed peak: first from the known target
    library (Stage A), then via untargeted composition search for the
    remainder (Stage B, configurable). Results are persisted as a new
    PeakAssignmentRun and readable via the sibling GET endpoints.

    :param sample_item_id: The unique identifier of the sample.
    :param body: Optional run configuration overrides.
    :param user: The current authenticated user. Requires workspace editor role.
    :param membership: Workspace membership with editor role on the sample.
    :return: Acknowledgement message with the background process id.
    """
    # Verify the existence of the sample item before queueing the task
    sample = await fetch_sample(sample_item_id)

    process_id = gen_id(8)
    background_tasks.add_task(
        assign_sample_peaks,
        sample_item_id=sample_item_id,
        config=body.config if body else None,
        independent_transaction=True,
        user_id=user.id,
        process_id=process_id,
    )
    return {
        "message": (
            f"Assigning peaks for sample '{sample.sample_item_name}', please wait."
        ),
        "process_id": process_id,
    }
