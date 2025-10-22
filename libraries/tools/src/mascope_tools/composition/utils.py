import re
import pandas as pd
import numpy as np
import ruptures as rpt
from pyteomics.mass import Composition, calculate_mass
from mascope_tools.composition.models import (
    CompositionFinderException,
    IonizationMechanism,
    Atom,
)
from mascope_tools.composition.constants import ELECTRON_MASS


def combine_formula_and_ionization(
    formula: str, ionization_mechanism: IonizationMechanism
) -> str:
    """
    Combine a neutral formula and ionization into a single ion formula in Hill notation.
    """
    # Parse formula
    comp_formula = Composition(formula=formula)
    comp_ionization = (
        Composition(formula=ionization_mechanism.formula)
        if ionization_mechanism
        else Composition(formula="")
    )
    if ionization_mechanism.addition:
        combined_composition = comp_formula + comp_ionization
    else:
        combined_composition = comp_formula - comp_ionization

    charge_sign = (
        "+" if ionization_mechanism and ionization_mechanism.charge > 0 else "-"
    )
    ion_formula = to_hill_order(combined_composition) + charge_sign
    return ion_formula


def parse_composition(formula_string: str, multiplier: int = 1) -> Composition:
    """Recursevely parses formulas like "(CH3CH2)2NH", "((CH3CH2)2NH)H", "(C6H10O2)H", "CH4N2OH"
    into pyteomics.Composition

    :param formula_string: String containing the formula to parse.
    :type formula_string: str
    :param multiplier: Multiplier after brackets, defaults to 1
    :type multiplier: int, optional
    :return: Parsed composition as a pyteomics.Composition object.
    :rtype: Composition
    """
    pattern = r"(\([^\(\)]+\))(\d*)"
    elements = Composition(formula="")
    i = 0
    while i < len(formula_string):
        # Find next bracketed group
        match = re.search(pattern, formula_string[i:])
        if match:
            start = i + match.start()
            end = i + match.end()
            # Parse before bracket
            before = formula_string[i:start]
            elements = elements + parse_composition(before, 1)
            # Parse inside bracket
            group = match.group(1)[1:-1]
            group_mult = int(match.group(2)) if match.group(2) else 1
            elements = elements + parse_composition(group, group_mult)
            i = end
        else:
            # Parse remaining string (elements outside brackets)
            m = re.match(r"([A-Z][a-z]?)(\d*)", formula_string[i:])
            if m:
                elem = m.group(1)
                count = int(m.group(2)) if m.group(2) else 1
                elements[elem] += count * multiplier
                i += len(m.group(0))
            else:
                i += 1
    return elements


def to_hill_order(elements: dict) -> str:
    """Convert a dictionary of elements to Hill notation string."""
    # Filter out zero and negative counts (can be if -H- is the ionization mechanism)
    elements = {k: v for k, v in elements.items() if v > 0}
    atomic_symbols = list(elements.keys())
    atomic_symbols.sort(key=lambda x: (0 if x == "C" else 1 if x == "H" else 2, x))
    formula = "".join(
        f"{symbol}{elements[symbol] if elements[symbol] > 1 else ''}"
        for symbol in atomic_symbols
    )
    formula = remove_ones_from_formula(formula)
    return formula


def remove_ones_from_formula(formula: str) -> str:
    formula = re.sub(r"([A-Za-z]+)1(?![0-9])", r"\1", formula)
    return formula


def parse_ionization(ionization_string: str) -> IonizationMechanism:
    """Parse ionization mechanism string from Mascope format into an IonizationMechanism object.

    :param ionization_string: String representing the ionization mechanism.
    :type ionization_string: str
    :raises CompositionFinderException: If the ionization is unsupported.
    :return: Parsed IonizationMechanism object.
    :rtype: IonizationMechanism
    """
    ionization_string = ionization_string.strip()
    formula = ""
    mass = ELECTRON_MASS
    if ionization_string == "+":
        # Abstract electron being kicked out
        addition = False
        charge = 1
    elif ionization_string == "-":
        # Abstract electron being added
        addition = True
        charge = -1
    elif ionization_string == "-H-":
        # Deprotonation
        addition = False
        formula = "H"
        charge = -1
        mass = calculate_mass(formula="H")
    else:
        # Regex pattern: start charge, base, end charge
        pattern = r"^([+-])?(.*?)([+-])?$"

        match = re.match(pattern, ionization_string)
        if match:
            addition = match.group(1) == "+"
            composition = parse_composition(match.group(2))
            formula = to_hill_order(composition)
            charge = 1 if match.group(3) == "+" else -1
            mass = composition.mass() - ELECTRON_MASS * charge
        else:
            raise CompositionFinderException(
                f"Unsupported ionization mechanism: '{ionization_string}'"
            )

    ionization_mech = IonizationMechanism(
        mascope_notation=ionization_string,
        addition=addition,
        formula=formula,
        mass=mass,
        charge=charge,
    )

    return ionization_mech


def parse_bool(val):
    """Parse a value into a boolean."""
    return str(val).lower() in ("1", "true", "yes", "on")


def parse_atom_count_ranges(count_ranges: str) -> list:
    """Parse a string of element count ranges into a list of Atom objects.

    :param count_ranges: String containing element count ranges.
        e.g. "C0-30 H0-40 N0-3 O0-20 O[18]0-1 C[13]0-2"
    :type count_ranges: str
    :return: List of Atom objects.
    :rtype: list
    """
    pattern = r"([A-Z][a-z]?(?:\[\d+\])?)(\d+)-(\d+)"
    atoms = []
    for match in re.finditer(pattern, count_ranges):
        element, min_count, max_count = match.groups()
        atoms.append(
            Atom(
                symbol=element,
                min_count=int(min_count),
                max_count=int(max_count),
                mass=calculate_mass(formula=element, charge=0),
            )
        )
    return atoms


def rank_matches_by_peak_presence(
    matches: pd.DataFrame, matched_peak_timeseries: pd.DataFrame
) -> pd.DataFrame:
    """Rank matches by the number of scans in which their corresponding peaks appear."""
    appearance = (matched_peak_timeseries.values > 0).sum(axis=1)
    peak_appearance_df = pd.DataFrame(
        {"mz": matched_peak_timeseries.index, "appearance": appearance}
    )

    ranked = matches.merge(
        peak_appearance_df, on="mz", how="left", suffixes=("", "_diff")
    ).sort_values(by="appearance", ascending=False)
    return ranked


def assign_intensity_change_score(
    matches: pd.DataFrame,
    matched_peak_timeseries: pd.DataFrame,
    n_changepoints: int = 2,
    smoothing_window: int = 11,
) -> pd.DataFrame:
    """Calculates a intensity change score for each m/z timeseries.

    This score measures how well the timeseries is described by a
    step-function model (i.e., a series of flat, horizontal segments).
    A score near 1.0 means a perfect fit (thew timeseries contains peaks).
    A score near 0.0 means a poor fit (like a noisy flat line or a ramp).

    This uses the "Binseg" algorithm from the 'ruptures' library.

    :param matches: DataFrame of matches.
    :type matches: pd.DataFrame
    :param matched_peak_timeseries: DataFrame of matched peak timeseries.
    :type matched_peak_timeseries: pd.DataFrame
    :param n_changepoints: Number of changepoints to detect.
    :type n_changepoints: int, optional
    :param smoothing_window: Window size for rolling mean smoothing.
    :type smoothing_window: int, optional
    :return: matches with step change scores added.
    :rtype: pd.DataFrame
    """
    print("Assiging peak intensity change scores (may take minutes)...")
    results = []

    # Ensure window is odd
    if smoothing_window % 2 == 0:
        smoothing_window += 1

    for mz, series in matched_peak_timeseries.iterrows():

        # --- Handle missing points ---
        series_numeric = pd.to_numeric(series, errors="coerce")
        series_filled = series_numeric.interpolate(method="linear").bfill().ffill()

        # Handle edge cases
        if series_filled.isnull().all() or series_filled.nunique() == 1:
            results.append({"mz": mz, "intensity_change_score": 0})
            continue

        signal = series_filled.values
        n_points = len(signal)

        # Ensure we have enough points to fit the model
        if n_points < (n_changepoints + 1) * 2:
            results.append({"mz": mz, "intensity_change_score": 0})
            continue

        # --- Calculate total sum of squares ---
        # This is the "cost" of a 0-changepoint model (a single flat line)
        global_mean = np.mean(signal)
        sse_total = np.sum((signal - global_mean) ** 2)

        if sse_total == 0:
            # Already a perfect flat line
            results.append({"mz": mz, "intensity_change_score": 0})
            continue

        # --- Find change points ---
        # smooth data to help the detector find the location
        # of the change points, avoiding noise-driven false positives.
        smoothed_signal = (
            series_filled.rolling(window=smoothing_window, min_periods=1, center=True)
            .mean()
            .bfill()
            .ffill()
            .values
        )

        # Use binary segmentation to find n_changepoints
        algo = rpt.Binseg(model="l2").fit(smoothed_signal)
        try:
            bkps = algo.predict(n_bkps=n_changepoints)
        except rpt.exceptions.NotEnoughPoints:
            results.append({"mz": mz, "intensity_change_score": 0})
            continue

        # bkps gives the end index of each segment. Prepend 0.
        segment_indices = [0] + bkps

        # --- Calculate model sum of squares (SSE_model) ---
        # Calculate cost using the filled signal, but the
        # changepoints found from the smoothed signal.
        sse_model = 0
        for start, end in zip(segment_indices[:-1], segment_indices[1:]):
            segment = signal[start:end]
            if len(segment) > 0:
                segment_mean = np.mean(segment)
                sse_model += np.sum((segment - segment_mean) ** 2)

        # --- Calculate final score (R-squared-like) ---
        # 1.0 = perfect step model fit
        # 0.0 = step model is no better than a single flat line
        score = 1 - (sse_model / sse_total)

        results.append({"mz": mz, "intensity_change_score": score})

    if not results:
        return pd.DataFrame(columns=["mz", "intensity_change_score"])

    results_df = pd.DataFrame(results).set_index("mz")

    assigned = matches.merge(results_df, on="mz", how="left")

    return assigned
