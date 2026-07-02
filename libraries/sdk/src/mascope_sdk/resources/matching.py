"""Compound matching resource for the Mascope SDK."""

from typing import Any

from ._base import BaseResource


class MatchingResource(BaseResource):
    """Resource for compound matching operations.

    Provides methods to match peaks in samples against target compounds
    based on m/z values, isotope patterns, and other criteria.

    Example::

        from mascope_sdk import MascopeClient

        mascope = MascopeClient()

        # Match a single compound in a sample
        matches = mascope.matching.match_compound(
            sample_id="sample-123",
            formula="C6H12O6",
            name="Glucose",
        )

        # Match multiple compounds
        matches = mascope.matching.match_compounds(
            sample_id="sample-123",
            formulas=["C6H12O6", "C12H22O11"],
        )
    """

    def match_compound(
        self,
        sample_id: str,
        formula: str,
        name: str = "Unknown Compound",
        match_params: dict[str, Any] | None = None,
    ) -> dict | None:
        """Match a single compound in a sample.

        Searches for peaks in the sample that match the target compound formula,
        considering ionization patterns and isotope distributions.

        :param sample_id: The ID of the sample to search in.
        :type sample_id: str
        :param formula: Chemical formula of the target compound (e.g., "C6H12O6").
        :type formula: str
        :param name: Name of the compound for reference. Defaults to "Unknown Compound".
        :type name: str, optional
        :param match_params: Optional matching parameters to filter results:
            - ``mz_tolerance``: m/z tolerance in ppm
            - ``isotope_ratio_tolerance``: Tolerance for isotope ratio matching
            - ``peak_min_intensity``: Minimum peak intensity threshold
            - ``probable_match_threshold``: Threshold for probable matches
            - ``possible_match_threshold``: Threshold for possible matches
        :type match_params: dict[str, Any], optional
        :return: A dictionary containing match data with compound, ions, and isotopes.
                 Returns None if no matches are found.
        :rtype: dict | None
        :raises AuthenticationError: If authentication fails.
        :raises NotFoundError: If the sample is not found.
        :raises ValidationError: If parameters are invalid.
        :raises MascopeAPIError: If the API request fails.

        Example::

            matches = mascope.matching.match_compound(
                sample_id="sample-123",
                formula="C6H12O6",
                name="Glucose",
                match_params={
                    "mz_tolerance": 50,
                    "isotope_ratio_tolerance": 0.2,
                },
            )

            if matches:
                for ion in matches.get('ions', []):
                    print(f"Ion: {ion['formula']} at m/z {ion['mz']}")
        """
        body: dict[str, Any] = {
            "target_compound": {
                "target_compound_formula": formula,
                "target_compound_name": name,
            }
        }
        if match_params is not None:
            body["match_params"] = match_params

        return self._post(f"match/aggregate/sample/{sample_id}/compound", data=body)

    def match_compounds(
        self,
        sample_id: str,
        formulas: list[str],
        match_params: dict[str, Any] | None = None,
        ionization_mechanism_ids: list[str] | None = None,
    ) -> list[dict] | None:
        """Match multiple compounds in a sample.

        Searches for peaks in the sample that match any of the target compound
        formulas, considering ionization patterns and isotope distributions.

        :param sample_id: The ID of the sample to search in.
        :type sample_id: str
        :param formulas: List of chemical formulas to match
                         (e.g., ["C6H12O6", "C12H22O11"]).
        :type formulas: list[str]
        :param match_params: Optional matching parameters (see :meth:`match_compound`).
        :type match_params: dict[str, Any], optional
        :param ionization_mechanism_ids: Optional list of mechanism IDs to use.
        :type ionization_mechanism_ids: list[str], optional
        :return: A list of match-data dictionaries, one per compound.
                 Returns None if no matches are found.
        :rtype: list[dict] | None
        :raises AuthenticationError: If authentication fails.
        :raises NotFoundError: If the sample is not found.
        :raises ValidationError: If parameters are invalid.
        :raises MascopeAPIError: If the API request fails.

        Example::

            matches = mascope.matching.match_compounds(
                sample_id="sample-123",
                formulas=["C6H12O6", "C12H22O11", "C3H6O3"],
            )
        """
        body: dict[str, Any] = {
            "target_compound_formulas": formulas,
        }
        if match_params is not None:
            body["match_params"] = match_params
        if ionization_mechanism_ids is not None:
            body["ion_mechanism_ids"] = ionization_mechanism_ids

        return self._post(f"match/aggregate/sample/{sample_id}/compounds", data=body)
