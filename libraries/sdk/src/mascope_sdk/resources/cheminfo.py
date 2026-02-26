"""Chemical information resource for the Mascope SDK."""

from __future__ import annotations

from ._base import BaseResource


class ChemInfoResource(BaseResource):
    """Resource for chemical information queries.

    Provides methods to query for potential elemental compositions based on
    m/z values and other parameters.

    Example::

        from mascope_sdk import MascopeClient

        mascope = MascopeClient()

        # Query potential formulas for a given m/z
        results = mascope.cheminfo.query_by_mz(
            mz=180.063,
            ionization_mechanism_ids=["mech-1", "mech-2"],
            mz_tolerance=30.0,
        )
        for result in results:
            print(f"{result['formula']}: {result['mass']}")
    """

    def query_by_mz(
        self,
        mz: float,
        ionization_mechanism_ids: list[str],
        formula_ranges: str = "C0-100 H0-100 O0-100 N0-100",
        mz_tolerance: float = 30.0,
        limit: int = 20,
    ) -> list[dict]:
        """Query potential elemental compositions for a given m/z value.

        Searches for chemical formulas that could produce the specified m/z
        value within the given tolerance, considering the specified ionization
        mechanisms.

        :param mz: The m/z value to query.
        :type mz: float
        :param ionization_mechanism_ids: List of ionization mechanism IDs to consider.
        :type ionization_mechanism_ids: list[str]
        :param formula_ranges: Element ranges to consider, e.g., "C0-100 H0-100 O0-100 N0-100".
                              Defaults to common organic elements.
        :type formula_ranges: str, optional
        :param mz_tolerance: The m/z tolerance in ppm. Defaults to 30.0.
        :type mz_tolerance: float, optional
        :param limit: Maximum number of results to return. Defaults to 20.
        :type limit: int, optional
        :return: A list of dictionaries containing potential elemental compositions,
                 each with formula, mass, and other chemical information.
        :rtype: list[dict]
        :raises AuthenticationError: If authentication fails.
        :raises ValidationError: If parameters are invalid.
        :raises MascopeAPIError: If the API request fails.

        Example::

            # Get ionization mechanisms first
            mechanisms = mascope.ionization.list()
            mech_ids = [m['id'] for m in mechanisms[:2]]

            # Query formulas
            results = mascope.cheminfo.query_by_mz(
                mz=180.063,
                ionization_mechanism_ids=mech_ids,
                formula_ranges="C0-20 H0-40 O0-10 N0-5",
                mz_tolerance=20.0,
                limit=10,
            )
        """
        return (
            self._post(
                "cheminfo/mz/query",
                data={
                    "mz": mz,
                    "mz_precision": mz_tolerance,
                    "formula_ranges": formula_ranges,
                    "ionization_mechanism_ids": ionization_mechanism_ids,
                    "limit": limit,
                },
            )
            or []
        )
