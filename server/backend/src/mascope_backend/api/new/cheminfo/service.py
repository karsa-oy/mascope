import traceback

import httpx
from sqlalchemy import select

from mascope_backend.api.controllers.match.aggregate.sample.match_aggregate_sample_controller import (
    aggregate_sample_match_compounds,
)
from mascope_backend.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_backend.api.new.cheminfo.config import cheminfo_config
from mascope_backend.api.new.cheminfo.utils import (
    to_cheminfo_ionization_format,
    to_explicit_isotope_format,
    to_mascope_ion_mech,
)
from mascope_backend.db import (
    IonizationMechanism,
    async_session,
)
from mascope_backend.runtime import runtime
from mascope_match.params import BaseMatchParams


@api_controller()
async def retrieve_cheminfo_by_mz(
    mz: float,
    ionization_mechanism_ids: list[str],
    mz_precision: float = cheminfo_config.DEFAULT_MZ_PRECISION,
    formula_ranges: str = cheminfo_config.DEFAULT_FORMULA_RANGE,
    sort: None | str = None,
    order: None | str = None,
) -> dict:
    """
    Query the ChemInfo database by mz and other optional parameters.

    Steps:
    - Fetch ionization mechanisms from database
    - Prepare request parameters and convert ionization mechanisms to ChemInfo format
      + Possible "custom elements" in formulas are converted to explicit isotope format,
        e.g. "^N" to "[15N]"
    - Make HTTP request to ChemInfo API
    - Process and format the results
      + Possible explicit isotope formats in formulas are reverted back to custom element format
        e.g. "[15N]" to "^N"
    - Apply sorting

    NOTE: Conversion between custom element notation and explicit isotope notation is only a
    best guess. E.g. "[15N]" will always be converted to "^N" even if the user intended to refer to
    the explicit isotope itself.

    :param mz: The m/z value to search for
    :type mz: float
    :param mz_precision: The tolerance for m/z matching in ppm
    :type mz_precision: float
    :param formula_ranges: Formula ranges permitted in the results
    :type formula_ranges: str
    :param ionization_mechanism_ids: List of ionization mechanism IDs to query against
    :type ionization_mechanism_ids: None | list[str]
    :param sort: Field to sort results by
    :type sort: None | str
    :param order: Sort order ('asc' or 'desc')
    :type order: None | str
    :return: Metadata and a result array of records containing the following fields:
        - target_compound_formula
        - target_compound_unsaturation
        - ionization_mechanism
        - target_isotope_mz
        - target_isotope_mz_error_ppm
    :rtype: dict
    """
    # Fetch ionization mechanisms from database
    async with async_session() as session:
        result = await session.execute(
            select(IonizationMechanism).filter(
                IonizationMechanism.ionization_mechanism_id.in_(
                    ionization_mechanism_ids
                )
            )
        )
        all_ionization_mechanisms = result.scalars().all()
        ionization_mechanisms = [
            i.ionization_mechanism for i in all_ionization_mechanisms
        ]
        if len(ionization_mechanisms) == 0:
            raise ValueError(
                f"No ionization mechanisms found with the provided IDs: {ionization_mechanism_ids}"
            )

    # Prepare request parameters and convert ionization mechanisms to ChemInfo format
    formula_ranges, custom_element_dict = to_explicit_isotope_format(formula_ranges)
    params = {
        "mass": mz,
        "ionizations": (
            ",".join([to_cheminfo_ionization_format(i) for i in ionization_mechanisms])
        ),
        "precision": mz_precision,
        "ranges": formula_ranges,
        "allowNeutral": "false",
    }
    # Make API request to ChemInfo
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{cheminfo_config.BASE_URL}/v1/mfFromMonoisotopicMass",
            params=params,
            timeout=cheminfo_config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()  # Raise exception for 4XX/5XX responses
        data = resp.json()

    # Process and format the results
    results = []
    for raw in data.get("result", []):
        # Process each compound result from ChemInfo
        try:
            formula = raw["mf"] if len(raw["mf"]) else "()"
            # Revert explicit isotope format back to custom element format
            for custom_elem, replaced_with in custom_element_dict.items():
                formula = formula.replace(replaced_with, custom_elem)
            results.append(
                {
                    "sample_peak_mz": mz,
                    "target_compound_formula": formula,
                    "target_compound_unsaturation": raw["unsaturation"],
                    "ionization_mechanism": to_mascope_ion_mech(
                        raw["ionization"]["mf"], all_ionization_mechanisms
                    ),
                    "target_isotope_mz": raw["ms"]["em"],
                    "target_isotope_mz_error_ppm": raw["ms"]["ppm"],
                }
            )
        except Exception as e:
            runtime.logger.error(
                f"Error processing result {raw}:\n{e}: {traceback.format_exc()}"
            )
            # Skip malformed results rather than failing the entire request
            continue

    # Apply sorting
    total_results = len(results)

    # Apply sorting if requested
    sorted_results = results
    if sort and all(sort in item for item in results):
        reverse = order.lower() == "desc"
        sorted_results.sort(key=lambda x: x.get(sort, 0), reverse=reverse)

    # Return formatted response
    return {
        "message": f"Retrieved {len(sorted_results)} m/z query results from ChemInfo",
        "results": len(sorted_results),
        "total": total_results,
        "data": sorted_results,
    }


@api_controller_background_task(
    success_notification_rooms=["user_id"],
    error_notification_rooms=["user_id"],
)
async def match_cheminfo_by_mz(
    sample_item_id: str,
    mz: float,
    mz_precision: float = 30,
    formula_ranges: str | None = "C0-100 H0-100 O0-100 N0-100",
    ionization_mechanism_ids: list[str] | None = None,
    match_params: BaseMatchParams | None = None,
    sort: None | str = None,
    order: None | str = "asc",
    independent_transaction: bool = False,
    user_id: None | int = None,
    process_id: None | str = None,
    parent_id: None | str = None,
) -> dict:
    """
    Match a specific m/z value against molecular structures from ChemInfo and compute potential
    match data for specified sample.

    Steps:
    - Query ChemInfo for compounds matching the m/z value
    - Match these compounds against a specified sample
    - Combine and format the results

    Match ion aggregation level is used to represent the match score of each formula result.
    Match isotopes are included in the result data for more detailed information.

    :param sample_item_id: Sample item ID to match against
    :type sample_item_id: str
    :param mz: The m/z value to search for
    :type mz: float
    :param mz_precision: The tolerance for m/z matching in ppm
    :type mz_precision: float
    :param formula_ranges: Formula ranges permitted in the results
    :type formula_ranges: None | str
    :param ionization_mechanism_ids: List of ionization mechanism IDs to query against
    :type ionization_mechanism_ids: None | list[str]
    :param match_params: Parameters for customizing the matching algorithm
    :type match_params: None | BaseMatchParams
    :param sort: Field to sort results by
    :type sort: None | str
    :param order: Sort order ('asc' or 'desc')
    :type order: None | str
    :param independent_transaction: Whether this is an independent transaction
    :type independent_transaction: bool
    :param user_id: Current user triggered operation (for user notifications)
    :type user_id: int | None, optional
    :param process_id: Process ID for tracking
    :type process_id: None | str
    :param parent_id: Parent process ID for nested operations
    :type parent_id: None | str
    :return: Metadata and a result array of records containing the following fields:
        - target_compound_formula
        - target_compound_unsaturation
        - ionization_mechanism
        - target_isotope_mz
        - target_isotope_mz_error_ppm
    :rtype: dict
    """
    # Get ChemInfo data
    runtime.logger.info(f"Starting ChemInfo query for m/z {mz}")
    cheminfo_result = await retrieve_cheminfo_by_mz(
        mz=mz,
        ionization_mechanism_ids=ionization_mechanism_ids,
        mz_precision=mz_precision,
        formula_ranges=formula_ranges,
        sort=sort,
        order=order,
    )

    cheminfo_data = cheminfo_result.get("data", [])
    cheminfo_results = cheminfo_result.get("results", 0)
    cheminfo_total = cheminfo_result.get("total", 0)

    # Return early if no ChemInfo data
    if not cheminfo_data:
        return {
            "message": "No matching compositions found by ChemInfo for the specified m/z and parameters.",
            "results": 0,
            "total": 0,
            "data": [],
            "_notification_data": {
                "mz": mz,
                "sample_item_id": sample_item_id,
            },
        }

    # Get matches against the sample
    runtime.logger.info(
        f"Matching {cheminfo_results} compounds against sample {sample_item_id}"
    )

    # Compute matches for the ChemInfo results
    ## Matches are computed for all ionization mechanisms for each returned formula
    ## and later filtered to keep only the one matching the original ChemInfo result
    matches_result = await aggregate_sample_match_compounds(
        sample_item_id=sample_item_id,
        target_compound_formulas=[
            info["target_compound_formula"] for info in cheminfo_data
        ],
        ion_mechanism_ids=ionization_mechanism_ids,
        match_params=match_params,
    )

    matches = matches_result.get("data", [])

    # Combine results data with cheminfo data
    data = []
    for info in cheminfo_data:
        # Find match data for the current ChemInfo result
        match_index = next(
            (
                index
                for index, match_compound in enumerate(matches)
                if info["target_compound_formula"]
                == match_compound["target_compound_formula"]
            ),
            None,
        )
        if match_index is None:
            runtime.logger.warning(
                (
                    "Match data not found for ChemInfo result: ",
                    f"{info['target_compound_formula']}",
                )
            )
            runtime.logger.debug(f"ChemInfo result: {info}")
            # Skip this ChemInfo result if no match found
            continue
        match_compound = matches[match_index]

        # Iterate over match ions to find the one that matches the ionization mechanism
        # of the current ChemInfo result
        for match_ion in match_compound.get("children", []):
            match_ion.update(
                {"target_compound_formula": info["target_compound_formula"]}
            )
            # Find isotopes matching the ionization mechanism
            info_ionization_mechanism = info.get("ionization_mechanism", {})
            if (
                match_ion["ionization_mechanism_id"]
                == info_ionization_mechanism["ionization_mechanism_id"]
            ):
                match_isotopes = match_ion.get("children", [])
                # Make sure the matched peak is the one in the original ChemInfo result
                # This is important because when computing matches, the closest peak
                # to target m/z is selected, which may not be the same as the one used in
                # the ChemInfo query.
                match_mzs = [iso["sample_peak_mz"] for iso in match_isotopes]
                if not info["sample_peak_mz"] in match_mzs:
                    runtime.logger.debug(
                        f"Requested peak m/z ({info['sample_peak_mz']}) is not in matched m/zs: {match_mzs}. "
                        + f"Skipping the result ({info["target_compound_formula"]})",
                    )
                    # Skip this result as the match is for a wrong peak
                    continue

                # Create combined result entry
                matched_info = {
                    **match_ion,
                    "cheminfo": info,
                    "children": match_isotopes,
                }
                data.append(matched_info)
                break

    # Return formatted response with notification data
    result_data = {
        "results": len(data),
        "total": cheminfo_total,
        "data": data,
    }
    message = (
        f"Matched {len(data)} potential compounds with m/z {mz:.4f} from ChemInfo."
    )
    runtime.logger.info(message)
    return {
        "message": message,
        **result_data,
        "_notification_data": {
            "mz": mz,
            "sample_item_id": sample_item_id,
            **result_data,
        },
    }
