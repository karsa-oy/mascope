"""Based on https://github.com/cheminfo/chemcalc"""

import warnings
import pandas as pd
import polars as pl
import numpy as np
from pyteomics.mass import calculate_mass
from mascope_tools.composition.heuristic_filter import (
    apply_heuristic_rules,
    match_isotopic_pattern,
)
from mascope_tools.composition import utils
from mascope_tools.composition.models import (
    SearchContext,
    Atom,
    Result,
    CompositionFinderWarning,
)
from mascope_tools.composition.constants import (
    DEFAULT_SEARCH_ELEMENT_COUNT_RANGES,
    DEFAULT_MAXIMUM_ROWS,
    UNSATURATION_COEFFICIENTS,
    DEFAULT_MASS_RANGE_THRESHOLD_PPM,
)


def assign_compositions(
    peaks: pd.DataFrame, params: dict, heuristic_params: dict = {}
) -> pd.DataFrame:
    """Assign molecular compositions to a DataFrame based on given params."""
    # Convert peaks to Polars DataFrame for better performance
    peaks = pl.from_pandas(peaks)
    peak_height_threshold = params.get("peak_height_threshold", 0.0)
    peaks_to_match = peaks.filter(pl.col("intensity") >= peak_height_threshold).sort(
        "intensity", descending=True
    )

    masses = peaks_to_match["mz"].to_numpy()
    results_per_peak = []
    assigned_mzs = set()

    for mass in masses:
        if mass in assigned_mzs:
            continue  # Skip if this mass has already been processed
        assigned_mzs.add(mass)
        params["monoisotopic_mass"] = mass
        params["target_monoisotopic_mass"] = mass
        compositions = find_compositions(params)

        # Guard for empty results
        comp_results = compositions.get("results", [])
        all_candidates = (
            ", ".join([r["formula"] for r in comp_results[1:]])
            if len(comp_results) > 1
            else ""
        )

        if comp_results:
            results = apply_heuristic_rules(comp_results, params=heuristic_params)
            # Fast path: if nothing survives heuristics, avoid isotopic work
            if results:
                results, composition_isotope_masses = match_isotopic_pattern(
                    results, peaks
                )
            else:
                composition_isotope_masses = np.array([])
            if not results:
                # No valid result for this peak
                results_per_peak.append(
                    {
                        "formula": "Undefined",
                        "mz": mass,
                        "other_candidates": all_candidates,
                    }
                )
                continue
            main_result = results[0].copy()
            main_result["mz"] = mass
            main_result["formula"] = main_result.get("formula", "Undefined")
            main_result["other_candidates"] = all_candidates
            results_per_peak.append(main_result)
        else:
            results_per_peak.append(
                {"formula": "Undefined", "mz": mass, "other_candidates": ""}
            )
            composition_isotope_masses = np.array([])

        # Assign isotope peaks to the closest unassigned masses (if any were detected)
        if composition_isotope_masses.size > 1:
            for iso_mz in composition_isotope_masses[1:]:
                if iso_mz == 0:
                    continue
                # Find closest mass to the isotope
                ind = (np.abs(masses - iso_mz)).argmin()
                closest = masses[ind]
                if closest in assigned_mzs:
                    continue
                assigned_mzs.add(closest)
                results_per_peak.append(
                    {
                        "formula": f"{main_result['formula']} isotope peak",
                        "mz": closest,
                        "other_candidates": "",
                    }
                )

    # Return compact Pandas DataFrame of assignments
    return pd.DataFrame(results_per_peak)


def find_compositions(params: dict[str, str]) -> dict:
    """Find molecular compositions based on given parameters.

    :param params: Dictionary containing search parameters.
    :param params['mass_range_ppm']: Allowed deviation from the target mass in ppm
    :param params['max_result_rows']: Maximum number of results to return.
    :param params['element_count_ranges']: Element count ranges in the format "C0-100 H0-202 N0-10 O0-10 C[13]0-3 O[18]0-3".
    :param params['monoisotopic_mass']: Target monoisotopic mass to search for.
    :param params['min_unsaturation']: Minimum unsaturation (double bond equivalents).
    :param params['max_unsaturation']: Maximum unsaturation (double bond equivalents).
    :param params['only_integer_unsaturation']: Whether to only consider integer unsaturation values.
    :param params['use_unsaturation']: Whether to use unsaturation in the search.
    :param params['return_result_count_only']: If True, only return the count of results.
    :param params['return_typed_format']: If True, return results in a typed format.

    :type params: dict[str, str]
    :raises CompositionFinderException: If the target monoisotopic mass is not greater than 0.
    :return: A dictionary containing the results of the search.
    :rtype: dict
    :yield: An iterator yielding dictionaries with molecular formula, mass, difference from target mass, and unsaturation.
    :rtype: Iterator[dict]
    """
    # --- Build search context from parameters ---
    ctx = SearchContext()
    ctx.mass_range = float(
        params.get("mass_range_ppm", DEFAULT_MASS_RANGE_THRESHOLD_PPM)
    )
    ctx.max_result_rows = int(params.get("max_result_rows", DEFAULT_MAXIMUM_ROWS))
    ctx.element_count_ranges = params.get(
        "element_count_ranges", DEFAULT_SEARCH_ELEMENT_COUNT_RANGES
    )
    ctx.min_unsaturation = float(params.get("min_unsaturation", 0))
    ctx.max_unsaturation = float(params.get("max_unsaturation", 50))
    ctx.only_integer_unsaturation = utils.parse_bool(
        params.get("only_integer_unsaturation", False)
    )
    ctx.use_unsaturation = utils.parse_bool(params.get("use_unsaturation", False))
    ctx.target_monoisotopic_mass = float(
        params.get("monoisotopic_mass", params.get("target_monoisotopic_mass", "-1"))
    )

    # --- Parse element count ranges ---
    element_ranges = utils.parse_atom_count_ranges(ctx.element_count_ranges)
    ctx.atoms = [
        Atom(el, minv, maxv, calculate_mass(formula=el, charge=0))
        for el, (minv, maxv) in element_ranges.items()
    ]

    # Sort atoms by mass to improve pruning efficiency
    ctx.atoms.sort(key=lambda a: a.mass)

    # --- Pruning arrays for search ---
    ctx.min_inner_mass, ctx.max_inner_mass = calc_min_max_inner_mass(ctx.atoms)

    # --- Perform search for neutral mass ---
    ionization_mech_string_list = get_ionization_mech_string_list(params)

    all_results = []
    for ionization_mech_string in ionization_mech_string_list:
        ctx.neutral_mass, ctx.ionization_mechanism = (
            get_neutral_mass_and_ionization_mech(
                ctx.target_monoisotopic_mass, ionization_mech_string
            )
        )
        # Compute absolute tolerance in Da
        ctx.abs_tolerance = max(ctx.neutral_mass * ctx.mass_range * 1e-6, 1e-6)

        # Handle pure ionization peak (neutral mass ~ 0 within a small absolute tolerance)
        if abs(ctx.neutral_mass) <= ctx.abs_tolerance:
            ion_formula = (
                ctx.ionization_mechanism.formula + "+"
                if ctx.ionization_mechanism and ctx.ionization_mechanism.charge > 0
                else (
                    ctx.ionization_mechanism.formula + "-"
                    if ctx.ionization_mechanism
                    else ""
                )
            )
            all_results.append(
                Result(
                    formula="Ionization peak",
                    neutral_mass=0.0,
                    error_ppm=0.0,
                    unsaturation=None,
                    ion=ion_formula,
                    ionization_mechanism=(
                        ctx.ionization_mechanism.mascope_notation
                        if ctx.ionization_mechanism
                        else None
                    ),
                    observed_mass=ctx.target_monoisotopic_mass,
                )
            )
            continue

        # Skip as peak not related to the current ionization mechanism
        if ctx.neutral_mass < 0:
            continue

        for i in recursive_search(0, [], 0.0, ctx):
            all_results.append(i)

    # --- Sort and format results ---
    all_results.sort(key=lambda r: r.error_ppm)

    return_result_count_only = utils.parse_bool(
        params.get("return_result_count_only", False)
    )
    return_typed_format = utils.parse_bool(params.get("return_typed_format", False))

    if return_result_count_only:
        return {"count": len(all_results)}

    return {
        "results": [format_result(r, return_typed_format) for r in all_results],
        "count": len(all_results),
        "options": params,
    }


def recursive_search(idx, counts, mass, ctx):
    """Recursive function to search for valid molecular compositions.

    :param idx: Current index in the atoms list.
    :type idx: int
    :param counts: List of counts for each atom in the current composition.
    :type counts: list[int]
    :param mass: Current mass of the composition being built.
    :type mass: float
    :param ctx: SearchContext containing search parameters and state.
    :type ctx: SearchContext
    :yield: A Result object if a valid composition is found.
    :rtype: Iterator[Result]
    """
    # Stop recursion if we've reached the max number of results
    if ctx.results_found >= ctx.max_result_rows:
        return

    if idx == len(ctx.atoms):
        # Use absolute Da tolerance for match
        if abs(mass - ctx.neutral_mass) <= ctx.abs_tolerance:

            if ctx.use_unsaturation:
                unsat = get_unsaturation(ctx.atoms, counts)
                if not (ctx.min_unsaturation <= unsat <= ctx.max_unsaturation):
                    return
                if ctx.only_integer_unsaturation and not unsat.is_integer():
                    return
            else:
                unsat = None

            formula = utils.to_hill_order(
                {ctx.atoms[i].symbol: counts[i] for i in range(len(ctx.atoms))}
            )
            ctx.results_found += 1  # Increment the counter
            ion_formula = utils.combine_formula_and_ionization(
                formula, ctx.ionization_mechanism
            )
            yield Result(
                formula=formula,
                neutral_mass=mass,
                error_ppm=(abs(mass - ctx.neutral_mass) / ctx.neutral_mass * 1e6),
                unsaturation=unsat,
                ion=ion_formula,
                ionization_mechanism=(
                    ctx.ionization_mechanism.mascope_notation
                    if ctx.ionization_mechanism
                    else None
                ),
                observed_mass=ctx.target_monoisotopic_mass,
            )
        return

    atom = ctx.atoms[idx]
    # Local references to speed attribute access
    min_inner = ctx.min_inner_mass
    max_inner = ctx.max_inner_mass
    target = ctx.neutral_mass
    tol = ctx.abs_tolerance

    for atom_count in range(atom.min_count, atom.max_count + 1):
        # Stop recursion if we've reached the max number of results
        if ctx.results_found >= ctx.max_result_rows:
            return
        new_mass = mass + atom_count * atom.mass
        if idx < len(ctx.atoms) - 1:
            # Tight pruning in Da
            min_mass = new_mass + min_inner[idx]
            max_mass = new_mass + max_inner[idx]
            # If even the minimal possible final mass is already too heavy -> break
            if (min_mass - target) > tol:
                break
            # If even the maximal possible final mass is still too light -> continue
            if (target - max_mass) > tol:
                continue
        yield from recursive_search(idx + 1, counts + [atom_count], new_mass, ctx)


def format_result(r, return_typed_format):
    """Format a Result object into a dictionary."""
    base = r.to_dict()
    base["formula"] = (
        {"type": "formula", "value": r.formula} if return_typed_format else r.formula
    )
    return base


def get_ionization_mech_string_list(options: dict) -> list:
    """Get a list of ionizations from the options dictionary."""
    ionizations = options.get("ionizations", "").strip()
    if ionizations:
        return [x.strip() for x in ionizations.split(",") if x.strip()]
    return [None]


def get_neutral_mass_and_ionization_mech(
    target_mass: float, ion: str
) -> tuple[float, str]:
    if ion:
        ionization_mech = utils.parse_ionization(ion)
        if ionization_mech.addition:
            # If it's an addition, we subtract mass
            neutral_mass = target_mass - ionization_mech.mass
        else:
            # If it's a subtraction, we add mass
            neutral_mass = target_mass + ionization_mech.mass
        return neutral_mass, ionization_mech
    return target_mass, None


def calc_min_max_inner_mass(atoms):
    """Calculate the minimum and maximum inner mass contributions for each atom."""
    n = len(atoms)
    min_inner = [0.0] * n
    max_inner = [0.0] * n
    for i in range(n):
        for j in range(i + 1, n):
            min_inner[i] += atoms[j].min_count * atoms[j].mass
            max_inner[i] += atoms[j].max_count * atoms[j].mass
    return min_inner, max_inner


def get_unsaturation(atoms: list[Atom], counts: list[int]) -> float:
    """Calculate the unsaturation (double bond equivalents) of a molecular formula.

    Warns if an atom's unsaturation coefficient is not supported.

    :param atoms: Iterable of Atom objects representing the elements in the formula.
    :type atoms: list[Atom]
    :param counts: List of counts for each atom in the formula.
    :type counts: list[int]
    :return: Unsaturation value (double bond equivalents).
    :rtype: float
    """
    unsaturation_value = 0
    for i, atom in enumerate(atoms):
        coefficient = UNSATURATION_COEFFICIENTS.get(atom.symbol, 0)
        if atom.symbol not in UNSATURATION_COEFFICIENTS:
            warnings.warn(
                f"Unsaturation coefficient for '{atom.symbol}' not supported, using {coefficient}.",
                CompositionFinderWarning,
            )
        unsaturation_value += coefficient * counts[i]
    return (unsaturation_value + 2) / 2.0
