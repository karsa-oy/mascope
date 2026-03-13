"""Sample batches resource for the Mascope SDK."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from .._resolve import resolve_id
from ._base import BaseResource


class BatchesResource(BaseResource):
    """Resource for sample batch operations.

    Sample batches group related samples together within a workspace.
    They contain metadata about the batch and references to individual samples.

    Example::

        from mascope_sdk import MascopeClient

        mascope = MascopeClient()

        # List batches by workspace name (substring match)
        batches = mascope.batches.list("My Workspace")

        # Or by workspace ID
        batches = mascope.batches.list("ws-123")
    """

    def _resolve_workspace_id(self, workspace: str) -> str:
        """Resolve a workspace name or ID to a workspace ID."""
        workspaces = self._client.workspaces.list()
        return resolve_id(
            workspace,
            workspaces,
            id_column="workspace_id",
            name_column="workspace_name",
            entity_label="workspace",
        )

    def list(self, workspace: str) -> pd.DataFrame | None:
        """List all sample batches in a workspace.

        :param workspace: Workspace name (or substring) or workspace ID.
        :type workspace: str
        :return: A DataFrame containing sample batch information with columns
                 including ``sample_batch_id`` and ``sample_batch_name``, or
                 None if no batches are found.
        :rtype: pd.DataFrame | None
        :raises ValueError: If the workspace cannot be resolved.
        :raises AuthenticationError: If authentication fails.
        :raises MascopeAPIError: If the API request fails.

        Example::

            # By name
            batches = mascope.batches.list("My Workspace")

            # By ID
            batches = mascope.batches.list("GwvleF1LJtEcfUQg")
        """
        workspace_id = self._resolve_workspace_id(workspace)
        return self._list_by_id(workspace_id)

    def _list_by_id(self, workspace_id: str) -> pd.DataFrame | None:
        """List batches by workspace ID (no name resolution)."""
        data = self._get("sample/batches", params={"workspace_id": workspace_id})
        if not data:
            return None
        return pd.DataFrame(data)

    def get_data(self, batch_id: str) -> dict[str, Any]:
        """Retrieve detailed data for all samples in a batch.

        This method fetches comprehensive data for a sample batch, including
        samples and combined match/targets data for compounds, ions, and isotopes.

        The data is retrieved in streaming mode to handle potentially large responses.

        :param batch_id: The ID of the sample batch to retrieve data for.
        :type batch_id: str
        :return: A dictionary containing:

                 - ``result``: Summary statistics about the retrieved data
                 - ``sample_batch``: Information about the sample batch
                 - ``samples``: A list of samples within the batch
                 - ``compounds``: Data for compounds (match + target data combined)
                 - ``ions``: Data for ions (match + target data combined)
                 - ``isotopes``: Data for isotopes (match + target data combined)
        :rtype: dict[str, Any]
        :raises AuthenticationError: If authentication fails.
        :raises NotFoundError: If the batch is not found.
        :raises MascopeAPIError: If the API request fails.

        Example::

            batch_data = mascope.batches.get_data(batch_id="batch-456")
            print(f"Batch: {batch_data['sample_batch']['name']}")
            print(f"Samples: {len(batch_data['samples'])}")
            print(f"Compounds: {len(batch_data['compounds'])}")
        """
        response = self._get(
            f"match/targets/batch/{batch_id}",
            stream=True,
        )

        # Parse streamed response
        try:
            chunks = []
            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    chunks.append(chunk)
            content = "".join(chunks)
            batch_data = json.loads(content)
        finally:
            response.close()

        if not batch_data:
            return {}

        # Extract and restructure the data
        return {
            "result": batch_data.get("result", {}),
            "sample_batch": batch_data.get("data", {}).get("sample_batch", {}),
            "samples": batch_data.get("data", {}).get("samples", []),
            "compounds": batch_data.get("data", {}).get("compounds", []),
            "ions": batch_data.get("data", {}).get("ions", []),
            "isotopes": batch_data.get("data", {}).get("isotopes", []),
        }
