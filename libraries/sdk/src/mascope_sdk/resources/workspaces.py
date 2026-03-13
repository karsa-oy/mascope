"""Workspaces resource for the Mascope SDK."""

from __future__ import annotations

import pandas as pd

from ._base import BaseResource


class WorkspacesResource(BaseResource):
    """Resource for workspace operations.

    Workspaces are the top-level organizational unit in Mascope, containing
    sample batches and related data.

    Example::

        from mascope_sdk import MascopeClient

        mascope = MascopeClient()

        # List all workspaces
        workspaces = mascope.workspaces.list()
        print(workspaces[["workspace_id", "name"]])
    """

    def list(self) -> pd.DataFrame | None:
        """List all accessible workspaces.

        :return: A DataFrame containing workspace information with columns
                 including ``workspace_id`` and ``name``, or None if no
                 workspaces are found.
        :rtype: pd.DataFrame | None
        :raises AuthenticationError: If authentication fails.
        :raises MascopeAPIError: If the API request fails.

        Example::

            workspaces = mascope.workspaces.list()
            print(workspaces[["workspace_id", "name"]])
        """
        cache_key = "workspaces"
        if cache_key in self._client._cache:
            return self._client._cache[cache_key]
        data = self._get("workspaces")
        if not data:
            return None
        df = pd.DataFrame(data)
        self._client._cache[cache_key] = df
        return df
