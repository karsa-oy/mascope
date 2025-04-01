import requests
import re
from sqlalchemy import (
    select,
)


from mascope_backend.db import async_session
from mascope_backend.db.models import (
    IonizationMechanism,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.controllers.match.aggregate.sample.match_aggregate_sample_controller import (
    aggregate_sample_match_compounds,
)
from mascope_backend.api.new.match.params import BaseMatchParams


chemcalc = "https://info.cheminfo.org"


@api_controller()
async def cheminfo_by_mz(
    mz: float,
    mz_precision: float = 30,
    formula_ranges: str | None = "C0-100 H0-100 O0-100 N0-100",
    ionization_mechanism_ids: list[str] | None = None,
    limit: int = 20,
) -> dict:
    """
    Query the ChemInfo database by mz and other optional parameters.

    :param mz: the m/z to search for
    :type mz: float
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

    async with async_session() as session:
        # Fetch the ionization mechanisms from the database using the extracted IDs
        result = await session.execute(
            select(IonizationMechanism).filter(
                IonizationMechanism.ionization_mechanism_id.in_(
                    ionization_mechanism_ids
                )
            )
        )
        all_ionization_mechanisms = result.scalars().all()

    if ionization_mechanism_ids:
        ionization_mechanisms = [
            i.ionization_mechanism for i in all_ionization_mechanisms
        ]
    else:
        ionization_mechanisms = []

    def to_cheminfo_str(ionization: str):
        polarity = ionization[-1]
        body = ionization[1:-1] if len(ionization) > 1 else ""
        operation = "-1" if ionization[0] == "-" else ""
        return f"{polarity}({body}){operation}"

    def to_mascope_ion_mech(ionization: str):
        pattern = r"^(\(-1\)|\+)\((.*?)\)(-1)?$"
        match = re.search(pattern, ionization)
        polarity = "-" if match.group(1) == "(-1)" else "+"
        body = match.group(2)
        operation = "-" if match.group(3) == "-1" else "+"
        ionization = f"{operation}{body}{polarity}" if len(body) > 0 else polarity
        return [
            mech
            for mech in all_ionization_mechanisms
            if mech.ionization_mechanism == ionization
        ][0].to_dict()

    params = {
        "mass": mz,
        "precision": mz_precision,
        "ranges": formula_ranges,
        "ionizations": ",".join([to_cheminfo_str(i) for i in ionization_mechanisms])
        if ionization_mechanisms
        else None,
        "allowNeutral": "false",
        "limit": limit,
    }
    resp = requests.get(f"{chemcalc}/v1/mfFromMonoisotopicMass", params=params)
    data = resp.json()
    results = [
        {
            "target_compound_formula": raw["mf"] if len(raw["mf"]) else "()",
            "target_compound_unsaturation": raw["unsaturation"],
            "ionization_mechanism": to_mascope_ion_mech(raw["ionization"]["mf"]),
            "target_isotope_mz": raw["ms"]["em"],
            "target_isotope_mz_error_ppm": raw["ms"]["ppm"],
        }
        for raw in data["result"]
    ]
    return {
        "message": f"Retrieved {len(results)} mz query results from ChemInfo",
        "results": len(results),
        "data": results,
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
