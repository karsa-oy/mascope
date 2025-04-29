import httpx
from sqlalchemy import select
from mascope_backend.db import async_session
from mascope_backend.db.models import (
    IonizationMechanism,
)
from mascope_backend.api.lib.api_features import (
    api_controller,
)
from mascope_backend.api.controllers.match.aggregate.sample.match_aggregate_sample_controller import (
    aggregate_sample_match_compounds,
)
from mascope_backend.api.new.match.params import BaseMatchParams
from mascope_backend.api.new.cheminfo.config import cheminfo_config
from mascope_backend.api.new.cheminfo.utils import (
    to_cheminfo_ionization_format,
    to_mascope_ion_mech,
)

from mascope_backend.runtime import runtime


@api_controller()
async def retrieve_cheminfo_by_mz(
    mz: float,
    mz_precision: float = 30,
    formula_ranges: None | str = "C0-100 H0-100 O0-100 N0-100",
    ionization_mechanism_ids: None | list[str] = None,
    limit: int = 20,
    page: int = 0,
    sort: None | str = None,
    order: None | str = None,
) -> dict:
    """
    Query the ChemInfo database by mz and other optional parameters.

    Steps:
    1. Fetch ionization mechanisms from database
    2. Prepare request parameters and convert ionization mechanisms to ChemInfo format
    3. Make HTTP request to ChemInfo API
    4. Process and format the results
    5. Apply pagination and sorting

    :param mz: The m/z value to search for
    :type mz: float
    :param mz_precision: The tolerance for m/z matching in ppm
    :type mz_precision: float
    :param formula_ranges: Formula ranges permitted in the results
    :type formula_ranges: None | str
    :param ionization_mechanism_ids: List of ionization mechanism IDs to query against
    :type ionization_mechanism_ids: None | list[str]
    :param limit: Maximum number of results to return
    :type limit: int
    :param page: Page number for pagination
    :type page: int
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
    # Step 1: Fetch ionization mechanisms from database
    async with async_session() as session:
        if ionization_mechanism_ids:
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
        else:
            all_ionization_mechanisms = []
            ionization_mechanisms = []

    # Step 2: Prepare request parameters and convert ionization mechanisms to ChemInfo format

    # NOTE: Don't pass the limit to get all total results, limit is used for results pagination
    # Cheminfo mfFromMonoisotopicMass limi default value : 1000
    params = {
        "mass": mz,
        # "limit": limit,
        "ionizations": (
            ",".join([to_cheminfo_ionization_format(i) for i in ionization_mechanisms])
            if ionization_mechanisms
            else None
        ),
        "precision": mz_precision,
        "ranges": formula_ranges,
        "allowNeutral": "false",
    }
    # Step 3: Make API request to ChemInfo
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{cheminfo_config.BASE_URL}/v1/mfFromMonoisotopicMass",
            params=params,
            timeout=cheminfo_config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()  # Raise exception for 4XX/5XX responses
        data = resp.json()

    # Step 4: Process and format the results
    results = []
    for raw in data.get("result", []):
        # Process each compound result from ChemInfo
        try:
            results.append(
                {
                    "target_compound_formula": raw["mf"] if len(raw["mf"]) else "()",
                    "target_compound_unsaturation": raw["unsaturation"],
                    "ionization_mechanism": to_mascope_ion_mech(
                        raw["ionization"]["mf"], all_ionization_mechanisms
                    ),
                    "target_isotope_mz": raw["ms"]["em"],
                    "target_isotope_mz_error_ppm": raw["ms"]["ppm"],
                }
            )
        except Exception as e:
            runtime.logger.error(repr(e))
            # Skip malformed results rather than failing the entire request
            continue

    # Step 5: Apply pagination and sorting
    total_results = len(results)

    # Apply pagination
    start_idx = page * limit
    end_idx = start_idx + limit
    paginated_results = results[start_idx:end_idx]

    # Apply sorting if requested
    if sort and sort in (paginated_results[0] if paginated_results else {}):
        reverse = order.lower() == "desc"
        paginated_results.sort(key=lambda x: x.get(sort, 0), reverse=reverse)

    # Return formatted response
    return {
        "message": f"Retrieved {len(paginated_results)} m/z query results from ChemInfo",
        "results": len(paginated_results),
        "total": total_results,
        "page": page,
        "data": paginated_results,
    }


@api_controller()
async def cheminfo_by_mz_matched(
    mz: float,
    sample_item_id: str,
    mz_precision: float = 30,
    formula_ranges: str | None = "C0-100 H0-100 O0-100 N0-100",
    ionization_mechanism_ids: list[str] | None = None,
    match_params: BaseMatchParams | None = None,
    limit: int = 20,
) -> dict:
    """
    Query the ChemInfo database by mz and other optional parameters.

    :param mz: the m/z to search for
    :type mz: float
    :param sample_item_id: the sample item ID to match for
    :param mzPrecision: the tolerance of m/z of matches to the queried m/z
    :type mzPrecision: float | None
    :param formulaRanges: formula ranges permitted in the results
    :type formulaRanges: str | None
    :param ionization_mechanisms: list of ionization mechanisms to query against
    :type ionization_mechanisms: list[str] | None
    :return: Metadata and a result array of records containing the following fields:
        - target_compound_formula
        - target_compound_unsaturation
        - ionization_mechanism
        - target_isotope_mz
        - target_isotope_mz_error_ppm
    :rtype: dict
    """
    cheminfo = (
        await cheminfo_by_mz(
            mz=mz,
            mz_precision=mz_precision,
            formula_ranges=formula_ranges,
            ionization_mechanism_ids=ionization_mechanism_ids,
            limit=limit,
        )
    )["data"]
    matches = (
        await aggregate_sample_match_compounds(
            sample_item_id=sample_item_id,
            target_compound_formulas=[
                info["target_compound_formula"] for info in cheminfo
            ],
            ion_mechanism_ids=ionization_mechanism_ids,
            match_params=match_params,
        )
    )["data"]
    results = [
        {
            **match,
            "cheminfo": info,
            "children": [
                ion["children"]
                for ion in match["children"]
                if ion["ionization_mechanism_id"]
                == info["ionization_mechanism"]["ionization_mechanism_id"]
            ][0],
        }
        for match, info in zip(matches, cheminfo)
    ]
    return {
        "message": f"Retrieved and matched {len(results)} mz query results from ChemInfo",
        "results": len(results),
        "data": results,
    }
