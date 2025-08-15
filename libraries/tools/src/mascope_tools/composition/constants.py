ELECTRON_MASS = 5.48579909065e-4

DEFAULT_MAXIMUM_ROWS = 1000
DEFAULT_SEARCH_ELEMENT_COUNT_RANGES = (
    "C0-100 H0-202 N0-10 O0-10 F0-3 Cl0-3 Br0-1 C[13]0-2 O[18]0-1"
)

MAXIMUM_UNSATURATION = 50.0
ISOTOPE_ABUNDANCE_THRESHOLD = 0.1
MZ_TOLERANCE_PPM = 1
ISOTOPIC_PATTERN_THRESHOLD = 0.5  # Threshold for isotopic pattern matching
MASS_RANGE_THRESHOLD_PPM = 1


# Wiley spectral database:
# H/C ratio 0.1...6.0 in 99.99% of all formulas.
ELEMENTAL_RATIO_RANGE = {
    "H/C": (0.1, 6.0),
    "N/C": (0.0, 2.0),
    "O/C": (0.0, 2.0),
    "S/C": (0.0, 0.1),
    "P/C": (0.0, 0.05),
    "Cl/C": (0.0, 0.05),
    "Br/C": (0.0, 0.05),
    "F/C": (0.0, 0.05),
    "I/C": (0.0, 0.05),
}

UNSATURATION_COEFFICIENTS = {
    "C": 2,
    "H": -1,
    "N": 1,
    "O": 0,
    "F": -1,
    "Cl": -1,
    "Br": -1,
    "I": -1,
    "C[13]": 2,
    "O[18]": 0,
}
