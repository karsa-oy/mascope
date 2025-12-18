"""
Utility functions for working with the ChemInfo API.
"""

import re

import mascope_molmass


def to_cheminfo_ionization_format(ionization: str) -> str:
    """
    Convert Mascope ionization mechanism format to ChemInfo API format.

    Mascope ionization mechanisms are defined in the format:
        <modification operation><modification formula><polarity>
    where:
    - "modification operation" is either "+" for addition or "-" for subtraction
    - "modification formula" is the chemical formula subtracted from or added to the parent molecule
    - "polarity" is the charge polarity of the resulting ion ("+" or "-").

    The ChemInfo API accepts ionizations in the format:
        <polarity>(<modification formula>)<modification operation>
    where:
    - "polarity" is the charge polarity of the resulting ion ("+" or "-")
    - "modification formula" is the chemical formula subtracted from or added to the parent molecule in the parentheses
    - "modification operation" is either "-1" for subtraction or "" (empty string) for addition.

    Examples how Mascope ionization mechanisms get converted:
    - "+H+" (Mascope) becomes "+(H)" (ChemInfo)
    - "-Cl-" (Mascope) becomes "-(Cl)-1" (ChemInfo)
    - "+" (Mascope) becomes "+()" (ChemInfo)

    :param ionization: Ionization mechanism string in Mascope format
    :type ionization: str
    :return: Ionization string formatted for ChemInfo API
    :rtype: str
    """
    polarity = ionization[-1]  # Last character is the charge polarity
    body = (
        ionization[1:-1] if len(ionization) > 1 else ""
    )  # Extract the middle part (if any)
    operation = (
        "-1" if ionization[0] == "-" else ""
    )  # Determine if this is a subtraction operation

    # Strip custom element notation from body for ChemInfo API
    body, _ = to_explicit_isotope_format(body)

    return f"{polarity}({body}){operation}"


def to_custom_element_format(formula: str) -> str:
    """
    Convert explicit isotope notation in a formula to custom element notation.

    Explicit isotopes are denoted with square brackets, e.g., "[15N]" for Nitrogen-15.
    This function replaces such notations with custom element notation, e.g., "^N", if
    the custom element exists, and its main isotope matches the specified isotope.

    :param formula: String containing a chemical formula with explicit isotopes.
        e.g. "C6H12[15N]O6"
    :type formula: str
    :return: String with custom element notation.
        e.g. "C6H12^NO6"
    :rtype: str
    """
    pattern = r"\[(\d+)([A-Z][a-z]?)\]"

    def replace_isotope(match):
        element = match.group(2)
        custom_element = f"^{element}"
        if custom_element in mascope_molmass.ELEMENTS:
            # Find the main isotope for this custom element
            main_isotope = None
            for iso in mascope_molmass.ELEMENTS[custom_element].isotopes.values():
                if main_isotope is None or iso.abundance > main_isotope.abundance:
                    main_isotope = iso
            # Check if the mass number of the custom element main isotope matches
            # with the specified isotope in the original formula
            if main_isotope.massnumber == int(match.group(1)):
                return custom_element
        # If no custom element found or mass number doesn't match, return original
        return match.group(0)

    result = re.sub(pattern, replace_isotope, formula)
    return result


def to_explicit_isotope_format(formula_ranges: str) -> str:
    """
    Convert custom element notation in formula ranges to explicit isotope notation.

    Custom elements are denoted with a caret (^) followed by the element symbol,
    e.g., "^N" for Nitrogen-15. This function replaces such notations with
    explicit isotope notation, e.g., "[15N]".

    :param formula_ranges: String containing element count ranges with custom elements.
        e.g. "C0-30 H0-40 O0-20 [13C]0-1 ^N0-1"
    :type formula_ranges: str
    :return: String with explicit isotope notation.
        e.g. "C0-30 H0-40 O0-20 [13C]0-1 [15N]0-1"
    :rtype: str
    """
    pattern = r"\^([A-Z][a-z]?)"
    replacements = {}

    def replace_custom_element(match):
        element = match.group(1)
        key = f"^{element}"
        main_isotope = None
        for iso in mascope_molmass.ELEMENTS[key].isotopes.values():
            if main_isotope is None or iso.abundance > main_isotope.abundance:
                main_isotope = iso
        replaced_with = f"[{main_isotope.massnumber}{element}]"
        replacements[key] = replaced_with
        return replaced_with

    result = re.sub(pattern, replace_custom_element, formula_ranges)
    return result, replacements


def to_mascope_ion_mech(ionization: str, all_ionization_mechanisms: list) -> dict:
    """
    Convert ChemInfo API ionization format back to Mascope format and find the matching mechanism.

    The ChemInfo API returns ionizations in formats like:
    - "+(H)+" for protonation
    - "(-)(Cl)-1" for deprotonation

    This function parses this format and finds the matching ionization mechanism in provided
    Mascope database ionization mechanisms.

    :param ionization: Ionization string in ChemInfo format
    :type ionization: str
    :param all_ionization_mechanisms: List of ionization mechanisms from the database
    :type all_ionization_mechanisms: List[IonizationMechanism]
    :return: Dictionary with ionization mechanism details
    :rtype: dict
    :raises ValueError: If the ionization format is invalid
    :raises IndexError: If no matching ionization mechanism is found
    """
    pattern = r"^(\(-1\)|\+)\((.*?)\)(-1)?$"
    match = re.search(pattern, ionization)

    if not match:
        raise ValueError(f"Invalid ionization format from ChemInfo: {ionization}")

    polarity = "-" if match.group(1) == "(-1)" else "+"
    body = match.group(2) or ""
    operation = "-" if match.group(3) == "-1" else "+"

    # Remove explicit isotope notation from body
    body = to_custom_element_format(body)

    # Reconstruct the Mascope ionization format
    ionization_str = f"{operation}{body}{polarity}" if body else polarity

    # Find matching mechanism in our database results all_ionization_mechanisms
    # will raise IndexError if not found
    return [
        mech
        for mech in all_ionization_mechanisms
        if mech.ionization_mechanism == ionization_str
    ][0].to_dict()
