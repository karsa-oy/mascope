"""
Utility functions for working with the ChemInfo API.
"""

import re


def to_cheminfo_ionization_format(ionization: str) -> str:
    """
    Convert Mascope ionization mechanism format to ChemInfo API format.

    The ChemInfo API expects ionizations in a specific format:
    - Positive charges as "H+", "Na+", "K+"
    - Negative charges in parentheses like "Cl(-)"
    - With optional additional modifiers

    Examples:
    - "+H+" (Mascope) becomes "+(H)+" (ChemInfo)
    - "-Cl-" (Mascope) becomes "(-)(Cl)-1" (ChemInfo)

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

    return f"{polarity}({body}){operation}"


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

    # Reconstruct the Mascope ionization format
    ionization_str = f"{operation}{body}{polarity}" if body else polarity

    # Find matching mechanism in our database results all_ionization_mechanisms
    # will raise IndexError if not found
    return [
        mech
        for mech in all_ionization_mechanisms
        if mech.ionization_mechanism == ionization_str
    ][0].to_dict()
