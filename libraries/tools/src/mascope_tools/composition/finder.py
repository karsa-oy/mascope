"""Based on https://github.com/cheminfo/chemcalc"""

import re
import warnings
from typing import Any
import pandas as pd
import polars as pl
import numpy as np
from IsoSpecPy import ParseFormula
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
    UNSATURATION_COEFFICIENTS,
)


def _is_notebook():
    try:
        from IPython import get_ipython

        shell = get_ipython().__class__.__name__
        return shell == "ZMQInteractiveShell"
    except Exception:
        return False


if _is_notebook():
    from tqdm.notebook import tqdm
else:
    from tqdm import tqdm


def assign_compositions(
    peaks: pd.DataFrame, params: dict, heuristic_params: dict | None = None
) -> pd.DataFrame:
    """Assign molecular compositions to a set of peaks.

    :param peaks: DataFrame with 'mz' and 'intensity' columns.
    :type peaks: pd.DataFrame
    :param params: Parameters for composition finding.
    :type params: dict
    :param heuristic_params: Parameters for heuristic filtering.
    :type heuristic_params: dict, optional
    :return: A DataFrame with assigned compositions and related information.
    :rtype: pd.DataFrame
    """
    # Convert peaks to Polars DataFrame
    peaks = pl.from_pandas(peaks).sort("mz")
    peak_height_threshold = params.get("peak_height_threshold", 0.0)
    peaks_to_match = peaks.filter(pl.col("intensity") >= peak_height_threshold)
    peaks_to_match = peaks_to_match.sort("mz")

    mzs = peaks_to_match["mz"].to_numpy()
    results_per_peak, assigned_mzs, mass_log_messages = [], set(), {}

    for mz in tqdm(mzs, desc="Assigning compositions..."):
        if mz in assigned_mzs:
            continue
        params["monoisotopic_mass"] = mz
        params["target_monoisotopic_mass"] = mz

        compositions = find_compositions(params)
        comp_results = compositions.get("results", [])
        all_candidates = (
            ", ".join([r["formula"] for r in comp_results[1:]])
            if len(comp_results) > 1
            else ""
        )

        if comp_results:
            candidates, log_messages = apply_heuristic_rules(
                comp_results, params=heuristic_params
            )
            mass_log_messages[mz] = log_messages
            if candidates:
                candidates, all_matched_isotopes = match_isotopic_pattern(
                    candidates, peaks
                )
            else:
                all_matched_isotopes = []
            if not candidates:
                results_per_peak.append(
                    {
                        "formula": "---",
                        "ion": "---",
                        "mz": mz,
                        "other_candidates": all_candidates,
                        "isotope_label": "---",
                    }
                )
                continue
            main_candidate = candidates[0].copy()
            main_candidate["mz"] = mz
            main_candidate["formula"] = main_candidate.get("formula", "---")
            main_candidate["other_candidates"] = all_candidates

            if all_matched_isotopes:
                isotopic_results, assigned_mzs = process_isotopes(
                    main_candidate, all_matched_isotopes, assigned_mzs
                )
                results_per_peak.extend(isotopic_results)
            else:
                # No isotopic pattern matched, just add the main result
                main_candidate["isotope_label"] = "M0"
                results_per_peak.append(main_candidate)
                assigned_mzs.add(main_candidate["mz"])

    unmatched_peaks = set(mzs) - assigned_mzs
    for mz in unmatched_peaks:
        results_per_peak.append(
            {
                "mz": mz,
                "formula": "---",
                "ion": "---",
                "isotope_label": "---",
                "other_candidates": "",
            }
        )

    matches = pd.DataFrame(results_per_peak)
    # --- Format results --- #
    matches = matches.sort_values(by=["mz", "mz_error_ppm"])
    # Drop duplicate m/z entries, keeping the one with the lowest mz_error_ppm
    matches = matches.drop_duplicates(subset=["mz"], keep="first")
    matches = sort_matches_by_formula(matches)
    # Add isotope label to ion string
    matches = update_ion_with_isotope_label(matches)
    # Show mz, formula, ion, isotope_label and then all other columns
    first_columns = ["mz", "formula", "ion", "isotope_label", "ionization_mechanism"]
    cols = first_columns + [col for col in matches.columns if col not in first_columns]
    matches = matches[cols].reset_index(drop=True)

    return matches, mass_log_messages


def process_isotopes(
    main_candidate: dict, all_matched_isotopes: list, assigned_mzs: set
) -> tuple:
    """Process and add isotopic pattern results

    :param main_candidate: Most likely composition for the monoisotopic m/z and related data.
    :type main_candidate: dict
    :param all_matched_isotopes: List of matched isotopic patterns.
    :type all_matched_isotopes: list
    :param assigned_mzs: The m/z values that have already been assigned to a composition.
    :type assigned_mzs: set
    :return: A tuple containing:
        - List of results per peak including isotopic variants.
        - Updated set of assigned m/z values.
    :rtype: tuple
    """
    results_per_peak = []
    # Take the first matched isotopic pattern (best scoring)
    matched_isotopes = all_matched_isotopes[0]
    isotope_mzs = matched_isotopes["masses"]
    isotope_labels = matched_isotopes["labels"]
    isotope_pred_mzs = matched_isotopes["predicted_masses"]
    isotope_pred_ints = matched_isotopes["predicted_intensities"]
    isotope_mz_errors = matched_isotopes["mass_errors_ppm"]
    isotope_intensity_errors = matched_isotopes["intensity_errors"]
    if isotope_mzs[0] != 0:
        # Extract and process base peak (M0)
        m0_mass = isotope_mzs[0]
        main_candidate["mz"] = m0_mass
        main_candidate["observed_mass"] = m0_mass
        main_candidate["predicted_mz"] = isotope_pred_mzs[0]
        main_candidate["predicted_intensity"] = isotope_pred_ints[0]
        main_candidate["isotope_label"] = "M0"
        main_candidate["mz_error_ppm"] = isotope_mz_errors[0]
        main_candidate["intensity_error"] = isotope_intensity_errors[0]
        results_per_peak.append(main_candidate)
        assigned_mzs.add(m0_mass)

        # Extract and process higher isotopes
        for idx in range(1, len(isotope_mzs)):
            iso_mz = isotope_mzs[idx]
            if iso_mz == 0:
                continue
            if iso_mz in assigned_mzs:
                continue
            iso_result = main_candidate.copy()
            iso_result["mz"] = iso_mz
            iso_result["observed_mass"] = iso_mz
            iso_result["isotope_label"] = isotope_labels[idx]
            iso_result["predicted_mz"] = isotope_pred_mzs[idx]
            iso_result["predicted_intensity"] = isotope_pred_ints[idx]
            iso_result["mz_error_ppm"] = isotope_mz_errors[idx]
            iso_result["intensity_error"] = isotope_intensity_errors[idx]
            iso_result["neutral_mass"] = iso_result["neutral_mass"] + (iso_mz - m0_mass)
            results_per_peak.append(iso_result)
            assigned_mzs.add(iso_mz)

    return results_per_peak, assigned_mzs


def find_compositions(params: dict[str, Any]) -> dict:
    """Find molecular compositions based on the provided parameters.

    :param params: Parameters for the composition search.
    :type params: dict[str, Any]
    :return: A dictionary containing the search results and related information.
    :rtype: dict
    """
    ctx = SearchContext()
    ctx.build(params)
    ctx.atoms = utils.parse_atom_count_ranges(ctx.element_count_ranges)
    ctx.atoms.sort(key=lambda a: a.mass)

    ctx.min_inner_mass, ctx.max_inner_mass = calc_min_max_inner_mass(ctx.atoms)

    ionization_mech_string_list = get_ionization_mech_string_list(params)

    target_mz = ctx.target_monoisotopic_mass
    ctx.abs_tolerance = target_mz * ctx.mass_range * 1e-6  # ppm -> Da around target m/z

    all_results: list[Result] = []

    for ionization_mech_string in ionization_mech_string_list:
        ionization_mech = utils.parse_ionization(ionization_mech_string)

        # Ion shift: ion m/z = neutral_mass + ion_shift
        ion_shift = (
            ionization_mech.mass if ionization_mech.addition else -ionization_mech.mass
        )
        required_neutral_mass = (
            target_mz - ion_shift
        )  # what neutral mass would give the target m/z

        # Ionization peak case: no analyte mass (neutral mass ~ 0)
        if abs(required_neutral_mass) <= ctx.abs_tolerance:
            ion_charge = "+" if ionization_mech.charge > 0 else "-"
            ion_formula = ionization_mech.formula + ion_charge
            all_results.append(
                Result(
                    formula="Ionization peak",
                    neutral_mass=0.0,
                    composition_error_ppm=0.0,
                    unsaturation=None,
                    ion=ion_formula,
                    ionization_mechanism=ionization_mech.mascope_notation,
                    observed_mass=target_mz,
                )
            )
            continue

        # Skip mechanisms that would imply negative / zero neutral masses
        if required_neutral_mass <= 0:
            continue

        # Store mechanism info in context for recursion
        ctx.ionization_mechanism = ionization_mech
        ctx.ion_shift = ion_shift
        ctx.results_found = 0  # reset per ionization mechanism

        for res in recursive_search(0, [], 0.0, ctx):
            all_results.append(res)

    all_results.sort(key=lambda r: r.composition_error_ppm)

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


def recursive_search(idx: int, counts: list, current_mass: float, ctx: SearchContext):
    """A recursive function to explore all possible combinations of atom counts.

    :param idx: Current index in the list of atoms.
    :type idx: int
    :param counts: Current counts of each atom type.
    :type counts: list
    :param current_mass: Current total mass of the composition.
    :type current_mass: float
    :param ctx: Search context containing parameters and state.
    :type ctx: SearchContext
    :yield: Result objects for valid compositions.
    :rtype: Iterator[Result]
    """
    if ctx.results_found >= ctx.max_result_rows:
        return

    # Evaluate full composition
    if idx == len(ctx.atoms):
        ion_mz = current_mass + ctx.ion_shift
        if abs(ion_mz - ctx.target_monoisotopic_mass) <= ctx.abs_tolerance:
            if ctx.use_unsaturation:
                unsat = get_unsaturation(ctx.atoms, counts)
                if not (ctx.min_unsaturation <= unsat <= ctx.max_unsaturation):
                    return
                if ctx.only_integer_unsaturation and not unsat.is_integer():
                    return
            else:
                unsat = None

            atomic_counts = {
                ctx.atoms[i].symbol: counts[i] for i in range(len(ctx.atoms))
            }
            formula = utils.to_hill_order(atomic_counts)
            ctx.results_found += 1
            ion_formula = utils.combine_formula_and_ionization(
                formula, ctx.ionization_mechanism
            )
            error_ppm = (
                abs(ion_mz - ctx.target_monoisotopic_mass)
                / ctx.target_monoisotopic_mass
                * 1e6
            )
            yield Result(
                formula=formula,
                neutral_mass=current_mass,
                composition_error_ppm=error_ppm,
                unsaturation=unsat,
                ion=ion_formula,
                ionization_mechanism=ctx.ionization_mechanism.mascope_notation,
                observed_mass=ctx.target_monoisotopic_mass,
            )
        return

    atom = ctx.atoms[idx]
    min_inner = ctx.min_inner_mass
    max_inner = ctx.max_inner_mass
    tol = ctx.abs_tolerance
    shift = ctx.ion_shift
    target_mz = ctx.target_monoisotopic_mass

    # Feasible count bounds for this atom (neutral mass domain)
    feasible_min = max(
        atom.min_count,
        int(
            np.ceil(
                ((target_mz - shift) - tol - current_mass - max_inner[idx]) / atom.mass
            )
        )
        - 1,
    )
    feasible_max = min(
        atom.max_count,
        int(
            np.floor(
                ((target_mz - shift) + tol - current_mass - min_inner[idx]) / atom.mass
            )
        )
        + 1,
    )
    if feasible_min > feasible_max:
        return

    for atom_count in range(feasible_min, feasible_max + 1):
        if ctx.results_found >= ctx.max_result_rows:
            return
        new_mass = current_mass + atom_count * atom.mass

        if idx < len(ctx.atoms) - 1:
            min_mass = new_mass + min_inner[idx]
            max_mass = new_mass + max_inner[idx]
            min_ion = min_mass + shift
            max_ion = max_mass + shift

            # Too heavy already (even minimal remaining mass overshoots)
            if (min_ion - target_mz) > tol:
                break
            # Still too light (even maximal remaining mass below window)
            if (target_mz - max_ion) > tol:
                continue

        yield from recursive_search(idx + 1, counts + [atom_count], new_mass, ctx)


def format_result(r, return_typed_format):
    """Format a Result object into a dictionary."""
    base = r.to_dict()
    base["formula"] = (
        {"type": "formula", "value": r.formula} if return_typed_format else r.formula
    )
    return base


def get_ionization_mech_string_list(params: dict) -> list:
    """Get a list of ionizations from the params dictionary."""
    ionizations = params.get("ionizations", None)
    if ionizations:
        return [ionization for ionization in ionizations.split(",")]
    else:
        raise ValueError("No ionization mechanisms provided.")


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
    """Prepare suffix arrays of minimal and maximal remaining masses AFTER each index.

    Returns:
        min_suffix[i]: minimal mass contribution of atoms with index > i
        max_suffix[i]: maximal mass contribution of atoms with index > i
        For convenience lengths match len(atoms); min_suffix[-1] == max_suffix[-1] == 0.
    """
    n = len(atoms)
    min_suffix = [0.0] * n
    max_suffix = [0.0] * n
    running_min = 0.0
    running_max = 0.0
    # Build from the end toward the front; suffix after i
    for i in range(n - 1, -1, -1):
        min_suffix[i] = running_min
        max_suffix[i] = running_max
        running_min += atoms[i].min_count * atoms[i].mass
        running_max += atoms[i].max_count * atoms[i].mass
    return min_suffix, max_suffix


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


def _formula_sort_key(formula: str) -> tuple[int, int, str]:
    """
    Generate a sorting key for a chemical formula based on atomic composition.
    Priority:
        0: Only C and H
        1: Only C, H, and O
        2: Only C, H, O, and N
        3: All other C-containing
        4: Non-carbon containing
    """
    try:
        atoms = set(ParseFormula(formula).keys())
        if "C" not in atoms:
            return (4, len(atoms), formula)
        if atoms <= {"C", "H"}:
            return (0, len(atoms), formula)
        if atoms <= {"C", "H", "O"}:
            return (1, len(atoms), formula)
        if atoms <= {"C", "H", "O", "N"}:
            return (2, len(atoms), formula)
        return (3, len(atoms), formula)
    except Exception:
        return (5, 0, formula)  # Place invalid formulas at the end


def sort_matches_by_formula(matches: pd.DataFrame) -> pd.DataFrame:
    """Sort a DataFrame of chemical formulae by atomic composition:
    1. C,H only
    2. C,H,O only
    3. C,H,O,N only
    4. Other C-containing
    5. Non-carbon containing
    Within each group, sort by number of atoms, then lexicographically.

    :param matches: Dataframe with matched peaks
    :type matches: pd.DataFrame
    :return: Sorted matches
    :rtype: pd.DataFrame
    """
    sort_keys = matches["formula"].apply(_formula_sort_key)
    return (
        matches.assign(_sort_key=sort_keys)
        .sort_values("_sort_key")
        .drop("_sort_key", axis=1)
        .reset_index(drop=True)
    )


def replace_atom_with_isotope(ion_formula: str, isotope_label: str) -> str:
    """Replace atoms in ion formula with their corresponding isotopic labels.

    :param ion_formula: Formula of the ion, Hill order, with a charge at the end.
    :type ion_formula: str
    :param isotope_label: Label of the isotope to replace, e.g. "13C", "13C+2H", "13C3".
    :type isotope_label: str
    :return: Modified ion formula with isotopes.
    :rtype: str
    """
    if not isinstance(isotope_label, str) or isotope_label in {"M0", "---", ""}:
        return ion_formula
    isotope_labels = [f"[{iso_label}]" for iso_label in isotope_label.split("+")]

    # Separate the charge at the end of the formula, if any
    ion_charge = ion_formula[-1] if ion_formula[-1] in "+-" else ""
    ion_formula = ion_formula[:-1] if ion_charge else ion_formula
    element_counts = ParseFormula(ion_formula)

    new_formula_parts = []
    for iso in isotope_labels:
        # Match isotope label with optional count, e.g. [13C2]
        element_match = re.match(r"\[(\d+)([A-Z][a-z]*)(\d*)\]", iso)
        if not element_match:
            raise ValueError(f"Invalid isotope label: {iso}.")

        isotope_mass = element_match.group(1)
        isotope_element = element_match.group(2)
        isotope_count_str = element_match.group(3)
        isotope_count = int(isotope_count_str) if isotope_count_str else 1

        # Check if the isotope's element exists in the formula
        if (
            isotope_element not in element_counts
            or element_counts[isotope_element] < isotope_count
        ):
            raise ValueError(
                f"Isotope element not found in the formula: {isotope_element}"
            )

        # Decrement the count of the target element
        element_counts[isotope_element] -= isotope_count

        # Add the isotope label to the formula parts
        new_formula_parts.append(
            f"[{isotope_mass}{isotope_element}]{isotope_count_str}"
        )

    # Rebuild the formula string
    for element in element_counts.keys():
        count = element_counts[element]
        if count == 0:
            continue  # Skip elements with a count of zero
        elif count == 1:
            new_formula_parts.append(element)
        else:
            new_formula_parts.append(f"{element}{count}")

    # Append the charge and join everything into the final string
    return "".join(new_formula_parts) + ion_charge


def update_ion_with_isotope_label(matches: pd.DataFrame) -> pd.DataFrame:
    """Update ion formulas in the matches DataFrame by replacing atoms with isotopic labels.

    :param matches: Matches DataFrame with 'ion' and 'isotope_label' columns.
    :type matches: pd.DataFrame
    :return: Updated matches DataFrame with modified 'ion' formulas.
    :rtype: DataFrame
    """
    matches = matches.copy()
    modified_ion_labels = []
    for ion, isotope_label in zip(matches["ion"], matches["isotope_label"]):
        try:
            updated_ion = replace_atom_with_isotope(ion, isotope_label)
        except ValueError:
            # If replacement fails, prepend empty brackets to indicate an issue
            updated_ion = f"[]{ion}"
        modified_ion_labels.append(updated_ion)

    matches["ion"] = modified_ion_labels
    return matches
