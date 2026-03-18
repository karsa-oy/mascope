"""Ionization mechanisms resource for the Mascope SDK."""

from __future__ import annotations

import pandas as pd

from ._base import BaseResource, _coerce_datetime_columns


class IonizationResource(BaseResource):
    """Resource for ionization mechanism operations.

    Ionization mechanisms describe how molecules become ions during mass spectrometry.
    They are used for compound matching and chemical formula queries.

    Example::

        from mascope_sdk import MascopeClient

        mascope = MascopeClient()

        # List available ionization mechanisms
        mechanisms = mascope.ionization.list()
        print(mechanisms[["ionization_mechanism_id", "ionization_mechanism"]])
    """

    def list(self) -> pd.DataFrame | None:
        """List all available ionization mechanisms.

        :return: A DataFrame containing ionization mechanism information with
                 columns including ``ionization_mechanism_id`` and ``ionization_mechanism``,
                 or None if no mechanisms are found.
        :rtype: pd.DataFrame | None
        :raises AuthenticationError: If authentication fails.
        :raises MascopeAPIError: If the API request fails.

        Example::

            mechanisms = mascope.ionization.list()
            protonation = mechanisms[
                mechanisms["ionization_mechanism"].str.contains("+H+")
            ]
        """
        cache_key = "ionization_mechanisms"
        if cache_key in self._client._cache:  # pylint: disable=protected-access
            return self._client._cache[cache_key]  # pylint: disable=protected-access
        data = self._get("ionization_mechanisms")
        if not data:
            return None
        df = _coerce_datetime_columns(pd.DataFrame(data))
        self._client._cache[cache_key] = df  # pylint: disable=protected-access
        return df
