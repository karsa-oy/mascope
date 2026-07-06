"""
SDK contract tests against a live demo stack.

These exercise ``MascopeClient`` end to end over HTTP, so they double as a
breaking-change detector for the REST API surface the SDK (and every external
SDK user) depends on: response envelopes, field names, and the data hierarchy
walk (workspace -> dataset -> batch -> sample -> peaks).

Opt-in: they need a running demo stack (snapshot mode) and are skipped
otherwise. Locally:

    docker compose -f docker-compose.demo.yaml up -d
    MASCOPE_SDK_CONTRACT=1 uv run pytest libraries/sdk/tests/ -v

In CI they run inside the demo-stack e2e job. Configuration:

- ``MASCOPE_SDK_TEST_URL``: app origin (default ``http://127.0.0.1:8080``).
- ``MASCOPE_SDK_TEST_TOKEN``: access token (default: the public demo token).
"""

import os

import pytest


BASE_URL = os.environ.get("MASCOPE_SDK_TEST_URL", "http://127.0.0.1:8080")
TOKEN = os.environ.get("MASCOPE_SDK_TEST_TOKEN", "mascope_demo_sdk_token")

requires_stack = pytest.mark.skipif(
    os.environ.get("MASCOPE_SDK_CONTRACT") != "1",
    reason=(
        "SDK contract tests need a running demo stack; start one "
        "(docker compose -f docker-compose.demo.yaml up -d) and set "
        "MASCOPE_SDK_CONTRACT=1"
    ),
)


def _workspace_with_data() -> str | None:
    """
    Name of the first workspace that has datasets (demo: 'Acquisitions Orbion').

    Auto-selection in ``MascopeClient`` refuses to pick when several
    workspaces exist (the demo stack also carries a system workspace), so the
    fixture resolves the data-bearing one explicitly. Uses the same headers
    the SDK sends.
    """
    import requests

    override = os.environ.get("MASCOPE_SDK_TEST_WORKSPACE")
    if override:
        return override

    headers = {"Authorization": f"Bearer {TOKEN}", "X-Service-Name": "mascope_sdk"}
    workspaces = requests.get(
        f"{BASE_URL}/api/workspaces", headers=headers, timeout=30
    ).json()["data"]
    for workspace in workspaces:
        datasets = (
            requests.get(
                f"{BASE_URL}/api/workspaces/{workspace['workspace_id']}/datasets",
                headers=headers,
                timeout=30,
            )
            .json()
            .get("data", [])
        )
        if datasets:
            return workspace["workspace_name"]
    return workspaces[0]["workspace_name"] if workspaces else None


@pytest.fixture(scope="module")
def mascope():
    """One authenticated client for the whole module, on the demo workspace."""
    from mascope_sdk import MascopeClient

    return MascopeClient(
        url=BASE_URL, access_token=TOKEN, workspace=_workspace_with_data()
    )


@requires_stack
class TestClientContract:
    def test_client_resolves_a_workspace(self, mascope):
        assert mascope.workspace_id
        assert mascope.workspace_name

    def test_workspaces_listing_shape(self, mascope):
        df = mascope.workspaces.list()

        assert df is not None and not df.empty
        assert {"workspace_id", "workspace_name"} <= set(df.columns)

    def test_datasets_listing_shape(self, mascope):
        df = mascope.datasets.list()

        assert df is not None and not df.empty, "demo stack should have datasets"
        assert {"dataset_id", "dataset_name"} <= set(df.columns)

    def test_batches_listing_shape(self, mascope):
        df = _first_batches(mascope)

        assert "sample_batch_id" in df.columns
        assert "sample_batch_name" in df.columns

    def test_samples_listing_shape(self, mascope):
        batch = _first_batches(mascope).iloc[0]

        df = mascope.samples.list(batch["sample_batch_id"])

        assert df is not None and not df.empty, "demo batch should have samples"
        assert {"sample_item_id", "filename"} <= set(df.columns)

    def test_sample_peaks_include_match_data(self, mascope):
        # The demo data ships fully matched, so peaks must carry flattened
        # match columns and at least one isotope attribution.
        sample_id = _first_sample_id(mascope)

        peaks = mascope.samples.get_peaks(sample_id)

        assert peaks is not None and not peaks.empty
        assert {"mz", "height", "target_isotope_id", "target_isotope_formula"} <= set(
            peaks.columns
        )
        assert peaks["target_isotope_id"].notna().any(), "expected matched peaks"

    def test_get_single_sample(self, mascope):
        sample_id = _first_sample_id(mascope)

        sample = mascope.samples.get(sample_id)

        assert sample is not None
        assert sample.get("sample_item_id") == sample_id


def _first_batches(mascope):
    """
    Batches of the first demo dataset that has any.

    Dataset ordering is not part of the contract, and the workspace can carry
    empty datasets (e.g. auto-created acquisition pools), so scan rather than
    trust ``iloc[0]``.
    """
    for _, dataset in mascope.datasets.list().iterrows():
        batches = mascope.batches.list(dataset["dataset_id"])
        if batches is not None and not batches.empty:
            return batches
    pytest.fail("demo stack has no dataset with batches")


def _first_sample_id(mascope) -> str:
    """A sample from the first batch of the first data-bearing dataset."""
    batch = _first_batches(mascope).iloc[0]
    samples = mascope.samples.list(batch["sample_batch_id"])
    assert samples is not None and not samples.empty, "demo batch should have samples"
    return samples.iloc[0]["sample_item_id"]
