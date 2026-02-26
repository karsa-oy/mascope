"""Workspaces resource for the Mascope SDK."""

from __future__ import annotations

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
        for ws in workspaces:
            print(f"{ws['name']}: {ws['id']}")
    """

    def list(self) -> list[dict]:
        """List all accessible workspaces.

        :return: A list of workspace dictionaries, each containing at least
                 ``id`` (unique workspace identifier), ``name`` (workspace name),
                 and additional workspace metadata.
        :rtype: list[dict]
        :raises AuthenticationError: If authentication fails.
        :raises MascopeAPIError: If the API request fails.

        Example::

            workspaces = mascope.workspaces.list()
            for ws in workspaces:
                print(f"Workspace: {ws['name']} (ID: {ws['id']})")
        """
        return self._get("workspaces") or []
