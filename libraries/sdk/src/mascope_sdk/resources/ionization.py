"""Ionization mechanisms resource for the Mascope SDK."""

from __future__ import annotations

from ._base import BaseResource


class IonizationResource(BaseResource):
    """Resource for ionization mechanism operations.

    Ionization mechanisms describe how molecules become ions during mass spectrometry.
    They are used for compound matching and chemical formula queries.

    Example::

        from mascope_sdk import MascopeClient

        mascope = MascopeClient()

        # List available ionization mechanisms
        mechanisms = mascope.ionization.list()
        for mech in mechanisms:
            print(f"{mech['name']}: {mech['id']}")
    """

    def list(self) -> list[dict]:
        """List all available ionization mechanisms.

        :return: A list of ionization mechanism dictionaries, each containing
                 ``id`` (unique mechanism identifier), ``name`` (mechanism name),
                 and additional mechanism metadata.
        :rtype: list[dict]
        :raises AuthenticationError: If authentication fails.
        :raises MascopeAPIError: If the API request fails.

        Example::

            mechanisms = mascope.ionization.list()
            protonation_ids = [
                m['id'] for m in mechanisms
                if 'protonation' in m['name'].lower()
            ]
        """
        return self._get("ionization_mechanisms") or []
