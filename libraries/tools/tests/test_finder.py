import pytest

from mascope_tools.composition.finder import replace_atom_with_isotope


def test_replace_atom_with_isotope():
    """Test the replace_atom_with_isotope function with various cases."""
    # ion, isotope label, expected output
    test_cases = [
        ("C6H12O6+", "13C", "[13C]C5H12O6+"),  # single carbon replacement
        ("C6H12O6+", "13C3", "[13C]3C3H12O6+"),  # multiple carbon replacement
        (
            "C6H12O6+",
            "13C3+2H",
            "[13C]3[2H]C3H11O6+",
        ),  # carbon and hydrogen replacement
        (
            "C6H12O6+",
            "13C3+2H2",
            "[13C]3[2H]2C3H10O6+",
        ),  # carbon and multiple hydrogen replacement
    ]
    for ion, isotope_label, expected in test_cases:
        result = replace_atom_with_isotope(ion, isotope_label)
        assert result == expected, (
            f"replace_atom_with_isotope({ion}, {isotope_label}) = {result}, expected {expected}"
        )

    # Cases that should raise ValueError
    error_cases = [
        ("C6H12O6+", "15N"),  # no nitrogen in formula
        ("C6H12O6+", "Karsa"),  # invalid isotope label
    ]
    for ion, isotope_label in error_cases:
        with pytest.raises(ValueError):
            replace_atom_with_isotope(ion, isotope_label)
