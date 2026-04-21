import re

from pyteomics.mass import Composition, calculate_mass

from mascope_tools.composition.config import ELECTRON_MASS
from mascope_tools.composition.exceptions import CompositionFinderException
from mascope_tools.composition.models import (
    Atom,
    IonizationMechanism,
)


def to_pyteomics(formula: str) -> str:
    """Convert bracket-first isotope notation to Pyteomics element-first.
    e.g. '[15N]O3' -> 'N[15]O3'
    """
    return re.sub(r"\[(\d+)([A-Z][a-z]?)\]", r"\2[\1]", formula)


def combine_formula_and_ionization(
    formula: str, ionization_mechanism: IonizationMechanism
) -> str:
    """
    Combine a neutral formula and ionization into a single ion formula in Hill notation.
    """
    # Parse formula (Pyteomics requires element-first notation)
    comp_formula = Composition(formula=to_pyteomics(formula))
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

    Examples
    --------
    >>> parse_composition("(CH3CH2)2NH", 1)
    Composition({'C': 4, 'H': 11, 'N': 1})
    >>> parse_composition("((CH3CH2)2NH)H", 1)
    Composition({'C': 4, 'H': 12, 'N': 1})
    >>> parse_composition("(C6H12O6)H", 1)
    Composition({'C': 6, 'H': 13, 'O': 6})
    >>> parse_composition("CH4N2OH", 1)
    Composition({'C': 1, 'H': 5, 'N': 2, 'O': 1})
    >>> parse_composition("HN^NO6", 1)
    Composition({'H': 1, 'N': 1, '^N': 1, 'O': 6})
    >>> parse_composition("[18O]C2H4^N", 1)
    Composition({'O': 1, 'C': 2, 'H': 4, '^N': 1})
    >>> parse_composition("H2O", 2)
    Composition({'H': 4, 'O': 2})
    >>> parse_composition("(H2O)", 2)
    Composition({'H': 4, 'O': 2})
    >>> parse_composition("(H2O)2", 1)
    Composition({'H': 4, 'O': 2})
    >>> parse_composition("((H2O)2)2", 1)
    Composition({'H': 8, 'O': 4})
    >>> parse_composition("^NO3", 1)
    Composition({'^N': 1, 'O': 3})
    >>> parse_composition("HHCCOO", 1)
    Composition({'H': 2, 'C': 2, 'O': 2})
    >>> parse_composition("", 1)
    Composition({})

    :param formula_string: String containing the formula to parse.
    :type formula_string: str
    :param multiplier: Multiplier after brackets, defaults to 1
    :type multiplier: int, optional
    :return: Parsed composition as a pyteomics.Composition object.
    :rtype: Composition
    """
    elements = Composition(formula="")
    s = formula_string
    while "(" in s:
        # Find the first '(' and its matching ')'
        open_idx = s.find("(")
        depth = 1
        close_idx = open_idx + 1
        while close_idx < len(s) and depth > 0:
            if s[close_idx] == "(":
                depth += 1
            elif s[close_idx] == ")":
                depth -= 1
            close_idx += 1
        if depth != 0:
            # Unmatched parenthesis, skip
            break
        # Extract group and multiplier
        group = s[open_idx + 1 : close_idx - 1]
        # Find multiplier after group
        mult_str = ""
        idx = close_idx
        while idx < len(s) and s[idx].isdigit():
            mult_str += s[idx]
            idx += 1
        group_mult = int(mult_str) if mult_str else 1
        before = s[:open_idx]
        after = s[idx:]
        elements += parse_composition(before, multiplier)
        elements += parse_composition(group, group_mult * multiplier)
        s = after
    # Parse remaining string (elements outside brackets)
    i = 0
    while i < len(s):
        m = re.match(r"(\^?[A-Z][a-z]?)(\d*)", s[i:])
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
    # For empty formula, return '()'
    if not elements:
        return "()"
    # Filter out zero and negative counts (can be if -H- is the ionization mechanism)
    elements = {k: v for k, v in elements.items() if v > 0}

    def normalize_symbol(symbol: str) -> str:
        # Accept both [15N] and N[15] and canonicalize to [15N].
        bracket_first = re.fullmatch(r"\[(\d+)([A-Z][a-z]?)\]", symbol)
        if bracket_first:
            return symbol

        element_first = re.fullmatch(r"([A-Z][a-z]?)\[(\d+)\]", symbol)
        if element_first:
            element, mass_num = element_first.groups()
            return f"[{mass_num}{element}]"

        return symbol

    normalized_elements = {}
    for symbol, count in elements.items():
        normalized_symbol = normalize_symbol(symbol)
        normalized_elements[normalized_symbol] = (
            normalized_elements.get(normalized_symbol, 0) + count
        )

    def hill_sort_key(symbol: str) -> tuple[int, str, int, int, str]:
        bracket_match = re.fullmatch(r"\[(\d+)([A-Z][a-z]?)\]", symbol)
        if bracket_match:
            mass_num, element = bracket_match.groups()
            priority = 0 if element == "C" else 1 if element == "H" else 2
            return (priority, element, 0, int(mass_num), symbol)

        plain_match = re.fullmatch(r"([A-Z][a-z]?)", symbol)
        if plain_match:
            element = plain_match.group(1)
            priority = 0 if element == "C" else 1 if element == "H" else 2
            return (priority, element, 1, 0, symbol)

        return (3, symbol, 1, 0, symbol)

    atomic_symbols = sorted(normalized_elements.keys(), key=hill_sort_key)
    formula = "".join(
        f"{symbol}{normalized_elements[symbol] if normalized_elements[symbol] > 1 else ''}"
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
        e.g. "C0-30 H0-40 N0-3 O0-20 [18O]0-1 [13C]0-2"
    :type count_ranges: str
    :return: List of Atom objects.
    :rtype: list
    """
    standard_pattern = re.compile(r"^([A-Z][a-z]?)(\d+)-(\d+)$")
    isotope_pattern = re.compile(r"^\[(\d+)([A-Z][a-z]?)\](\d+)-(\d+)$")
    legacy_isotope_pattern = re.compile(r"^[A-Z][a-z]?\[\d+\]\d+-\d+$")

    atoms = []
    tokens = count_ranges.split()
    for token in tokens:
        match = standard_pattern.fullmatch(token)
        if match:
            element, min_count, max_count = match.groups()
            symbol = element
            mass_formula = symbol
        else:
            match = isotope_pattern.fullmatch(token)
            if match:
                mass_number, element, min_count, max_count = match.groups()
                symbol = f"[{mass_number}{element}]"
                mass_formula = f"{element}[{mass_number}]"
            else:
                if legacy_isotope_pattern.fullmatch(token):
                    raise CompositionFinderException(
                        (
                            f"Invalid isotope format '{token}'. "
                            "Use bracket-first notation like '[15N]0-1'."
                        )
                    )
                raise CompositionFinderException(
                    f"Invalid element count range token '{token}'."
                )

        min_count_i = int(min_count)
        max_count_i = int(max_count)
        if min_count_i > max_count_i:
            raise CompositionFinderException(
                f"Invalid range '{token}': min count cannot exceed max count."
            )

        atoms.append(
            Atom(
                symbol=symbol,
                min_count=min_count_i,
                max_count=max_count_i,
                mass=calculate_mass(formula=mass_formula, charge=0),
            )
        )

    return atoms


def normalize_formula_with_isotopes(formula: str) -> str:
    """
    Normalize a chemical formula by removing explicit isotope notations.

    NOTE: This function does not combine isotopes with their non-isotopic counterparts,
    it simply removes the isotope brackets. Use `parse_composition` to get a combined composition
    if needed.

    Examples
    --------
    >>> normalize_formula_with_isotopes("HN^NO6")
    'HN^NO6'
    >>> normalize_formula_with_isotopes("[18O]C2H4^N")
    'OC2H4^N'
    >>> normalize_formula_with_isotopes("[18O]2C2H4^N")
    'O2C2H4^N'
    >>> normalize_formula_with_isotopes("C6H12O6")
    'C6H12O6'
    >>> normalize_formula_with_isotopes("[13C]C5[2H]H11[18O]O5")
    'CC5HH11OO5'
    >>> normalize_formula_with_isotopes("")
    ''

    :param formula: Chemical formula string, e.g. "[13C]H4[18O]"
    :type formula: str
    :return: Normalized formula string, e.g. "CH4O"
    :rtype: str
    """
    normalized_formula = re.sub(r"\[\d+([A-Za-z]+)\]", r"\1", formula)
    normalized_formula = re.sub(r"([A-Z][a-z]?)\[\d+\]", r"\1", normalized_formula)
    return normalized_formula
