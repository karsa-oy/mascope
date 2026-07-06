"""
Integration tests for the peak assignments read API.

Exercises the peaks-with-assignments and runs endpoints through the full
HTTP stack, including latest-completed-run resolution, filtering, 404
handling, and the editor-role requirement on the assign endpoint.
"""

import pytest


@pytest.mark.asyncio
async def test_get_runs_returns_all_runs_newest_first(guest_client, pa_test_data):
    response = await guest_client.get(
        f"/api/peak-assignments/sample/{pa_test_data['sample_item_id']}/runs"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == 2
    run_ids = [run["peak_assignment_run_id"] for run in body["data"]]
    assert run_ids == [
        pa_test_data["running_run_id"],
        pa_test_data["completed_run_id"],
    ]


@pytest.mark.asyncio
async def test_get_assignments_defaults_to_latest_completed_run(
    guest_client, pa_test_data
):
    response = await guest_client.get(
        f"/api/peak-assignments/sample/{pa_test_data['sample_item_id']}"
    )
    assert response.status_code == 200
    body = response.json()

    # The 'running' run is newer but not completed, so the completed run wins
    assert body["run"]["peak_assignment_run_id"] == pa_test_data["completed_run_id"]
    assert body["results"] == 3

    # One row per observed peak, ordered by m/z
    mzs = [row["sample_peak_mz"] for row in body["data"]]
    assert mzs == sorted(mzs)

    by_peak = {row["sample_peak_id"]: row for row in body["data"]}
    assert by_peak["peak-1"]["role"] == "M0"
    assert by_peak["peak-1"]["assigned_formula"] == "C6H12O6"
    assert (
        by_peak["peak-2"]["owner_peak_assignment_id"]
        == pa_test_data["m0_assignment_id"]
    )
    assert by_peak["peak-3"]["tier"] == "unassigned"
    assert by_peak["peak-3"]["assigned_formula"] is None


@pytest.mark.asyncio
async def test_get_assignments_supports_tier_and_role_filters(
    guest_client, pa_test_data
):
    sample_item_id = pa_test_data["sample_item_id"]

    response = await guest_client.get(
        f"/api/peak-assignments/sample/{sample_item_id}",
        params={"tier": "identified"},
    )
    assert response.status_code == 200
    assert response.json()["results"] == 2

    response = await guest_client.get(
        f"/api/peak-assignments/sample/{sample_item_id}",
        params={"role": "M0"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == 1
    assert body["data"][0]["sample_peak_id"] == "peak-1"

    response = await guest_client.get(
        f"/api/peak-assignments/sample/{sample_item_id}",
        params={"source": "database"},
    )
    assert response.status_code == 200
    assert response.json()["results"] == 2


@pytest.mark.asyncio
async def test_get_assignments_with_explicit_run_id(guest_client, pa_test_data):
    response = await guest_client.get(
        f"/api/peak-assignments/sample/{pa_test_data['sample_item_id']}",
        params={"peak_assignment_run_id": pa_test_data["running_run_id"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["run"]["peak_assignment_run_id"] == pa_test_data["running_run_id"]
    assert body["results"] == 0


@pytest.mark.asyncio
async def test_get_assignments_unknown_run_id_returns_404(guest_client, pa_test_data):
    response = await guest_client.get(
        f"/api/peak-assignments/sample/{pa_test_data['sample_item_id']}",
        params={"peak_assignment_run_id": "does-not-exist-42"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assign_requires_editor_role(guest_client, pa_test_data):
    response = await guest_client.post(
        f"/api/peak-assignments/sample/{pa_test_data['sample_item_id']}/assign"
    )
    assert response.status_code == 403
