# molmass.py

# Copyright (c) 1990-2020, Christoph Gohlke
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Molecular Mass Calculations.

Molmass is a Python library and console script to calculate the molecular mass
(average, nominal, and isotopic pure), the elemental composition, and the
mass distribution spectrum of a molecule given by its chemical formula,
relative element weights, or sequence.

Calculations are based on the isotopic composition of the elements. Mass
deficiency due to chemical bonding is not taken into account.

Examples of valid formulas are ``H2O``, ``[2H]2O``, ``CH3COOH``, ``EtOH``,
``CuSO4.5H2O``, ``(COOH)2``, ``AgCuRu4(H)2[CO]12{PPh3}2``, ``CGCGAATTCGCG``,
and ``MDRGEQGLLK``.

Formulas are case sensitive and ``+`` denotes the arithmetic operator,
not an ion charge.

For command line usage run ``python -m molmass --help``

:Author: `Christoph Gohlke <https://www.lfd.uci.edu/~gohlke/>`_

:License: BSD 3-Clause

:Version: 2020.6.10

Requirements
------------
* `CPython >= 3.6 <https://www.python.org>`_

Revisions
---------
2020.6.10
    Update elements_gui.py to version 2020.6.10.
2020.1.1
    Update elements.py to version 2020.1.1.
    Remove support for Python 2.7 and 3.5.
    Update copyright.
2018.8.15
    Move modules into molmass package.
2018.5.29
    Add option to start web interface from console.
2018.5.25
    Style and docstring fixes.
    Make 'from_fractions' output deterministic.
2005.x.x
    Initial release.

"""

__version__ = "2020.6.10"

__all__ = (
    "analyze",
    "Formula",
    "FormulaError",
    "Spectrum",
    "Composition",
    "test",
    "main",
    "from_elements",
    "from_sequence",
    "from_string",
    "hill_sorted",
    "GROUPS",
)

import copy
import math
import re
import sys
from functools import reduce


from mascope_chem.runtime import runtime

try:
    from elements import ELECTRON, ELEMENTS, Isotope
except ImportError:
    from .elements import ELECTRON, ELEMENTS, Isotope


def analyze(formula, maxatoms=250):
    """Return analysis of chemical formula as string.

    Calculate mass spectrum if number of atoms is smaller than maxatoms.

    """
    result = []
    try:
        f = Formula(formula)

        if len(str(f)) <= 50:
            result.append(f"Formula: {f}")
        result.append("Charge: %s%s" % (("+" if f.charge > 0 else ""), f.charge))
        if formula != f.formula:
            result.append(f"Hill notation: {f.formula}")
        if f.formula != f.empirical:
            result.append(f"Empirical formula: {f.empirical}")

        prec = precision_digits(f.mass, 9)
        if f.mass != f.isotope.mass:
            result.append(f"\nAverage mass: {f.mass:.{prec}f}")
        result.extend(
            (
                f"Monoisotopic mass: {f.isotope.mass:.{prec}f}",
                f"m/z:  {f.mz:.{prec}f}",
                f"Nominal mass: {f.isotope.massnumber}",
            )
        )

        c = f.composition()
        if len(c) > 1:
            result.extend(("\nElemental Composition\n", str(c)))

        if f.atoms < maxatoms:
            s = f.spectrum()
            if len(s) > 1:
                result.extend(
                    (
                        "\nMass Distribution",
                        f"\nMost abundant mass: {s.peak[0]:.{prec}f} "
                        f"({ s.peak[1] * 100:.3f}%)",
                        f"Mean mass: {s.mean:.{prec}f}\n",
                        str(s),
                    )
                )

    except Exception as exc:
        result.append(f"Error: {exc}")

    return "\n".join(result)


class lazyattr:
    """Lazy object attribute whose value is computed on first access."""

    def __init__(self, func):
        self.func = func
        # crude hack to keep docstrings and allow doctests
        if func.__doc__:
            self.__doc__ = func.__doc__
            lazyattr.docstrings.__doc__ += "\n\n" + func.__doc__

    def __get__(self, instance, owner):
        if instance is None:
            return self
        result = self.func(instance)
        if result is NotImplemented:
            return getattr(super(owner, instance), self.func.__name__)
        setattr(instance, self.func.__name__, result)
        return result

    @staticmethod
    def docstrings():
        """Docstrings of lazy attributes get appended to this string."""


class Formula:
    """Chemical formula.

    Input string may contain only symbols of chemical elements and isotopes,
    parentheses, and numbers.
    Calculate various properties from formula string, such as hill notation,
    empirical formula, mass, elemental composition, and mass distribution.
    Raise FormulaError on errors.

    Examples
    --------
    >>> Formula('H2O')
    Formula('H2O')

    """

    def __init__(self, formula="", groups=None):
        self._formula = from_string(formula, groups)

    def __str__(self):
        return self._formula

    def __repr__(self):
        return f"Formula('{self._formula}')"

    def __mul__(self, number):
        """Return this formula repeated number times as new Formula.

        Examples
        --------
        >>> Formula('H2O') * 2
        Formula('(H2O)2')

        """
        if not isinstance(number, int) or number < 1:
            raise TypeError("can only multipy with positive number")
        return Formula(f"({self._formula}){number}")

    def __rmul__(self, number):
        """Return this formula repeated number times as new Formula.

        Examples
        --------
        >>> 2 * Formula('H2O')
        Formula('(H2O)2')

        """
        return self.__mul__(number)

    def __add__(self, other):
        """Add this and other formula and return as new Formula.

        Examples
        --------
        >>> Formula("H2O") + Formula("H2O")
        Formula('(H2O)(H2O)')

        """
        if not isinstance(other, Formula):
            raise TypeError("can only add Formula instance")
        charge = self.charge + other.charge
        if charge == 0:
            return Formula(f"({self.formula})({other.formula})")
        elif charge == 1:
            return Formula(f"({self.formula})({other.formula})+")
        elif charge == -1:
            return Formula(f"({self.formula})({other.formula})-")
        elif charge > 0:
            return Formula(f"({self.formula})({other.formula})_{charge}+")
        elif charge < 0:
            return Formula(f"({self.formula})({other.formula})_{-charge}-")

    def __radd__(self, other):
        if other == 0:
            return self
        else:
            return self.__add__(other)

    def __sub__(self, other):
        """Subtract elements of other formula and return as new Formula.

        Examples
        --------
        >>> Formula('H2O') - Formula('O')
        Formula('H2')

        """
        if not isinstance(other, Formula):
            raise TypeError("can only subtract Formula instance")
        _elements = copy.deepcopy(self._elements)
        for symbol, isotopes in other._elements.items():
            if symbol not in _elements:
                raise ValueError(f"element {symbol} not in {self}")
            element = _elements[symbol]
            for massnumber, count in isotopes.items():
                if massnumber not in element:
                    raise ValueError(f"element {massnumber}{symbol} not in {self}")
                element[massnumber] -= count
                if element[massnumber] < 0:
                    raise ValueError(f"negative number of element {massnumber}{symbol}")
                if element[massnumber] == 0:
                    del element[massnumber]
                if not element:
                    del _elements[symbol]
        return Formula(from_elements(_elements))

    @lazyattr
    def _elements(self):
        """Return number of atoms and isotopes by element as dict.

        Return type is dict{element symbol: dict{mass number: count}}

        Examples
        --------
        >>> Formula('H')._elements
        {'H': {0: 1}}
        >>> pprint(Formula('[2H]2O')._elements)  # pprint sorts dict
        {'H': {2: 2}, 'O': {0: 1}}

        """
        formula = self._formula
        if not formula:
            raise FormulaError("empty formula", formula, 0)

        validchars = set("([{<123456789ABCDEFGHIKLMNOPRSTUVWXYZ_+-")

        if not formula[0] in validchars:
            raise FormulaError(f"unexpected character '{formula[0]}'", formula, 0)

        validchars |= set("]})>0abcdefghiklmnoprstuy")

        elements = {}
        ele = ""  # parsed element
        num = 0  # number
        level = 0  # parenthesis level
        counts = [1]  # parenthesis level multiplication
        i = len(formula)
        charge_mode = False
        while i:
            i -= 1
            char = formula[i]
            if char not in validchars:
                raise FormulaError(f"unexpected character {char}'", formula, i)
            if char in "([{<":
                level -= 1
                if level < 0 or num != 0:
                    raise FormulaError("missing closing parenthesis ')]}>'", formula, i)
            elif char in ")]}>":
                charge_mode = False
                if num == 0:
                    num = 1
                level += 1
                if level > len(counts) - 1:
                    counts.append(0)
                counts[level] = num * counts[level - 1]
                num = 0
            elif char in "+-":
                charge_mode = True
            elif char.isdigit():
                j = i
                while i and formula[i - 1].isdigit():
                    i -= 1
                if charge_mode:
                    num = 1
                else:
                    num = int(formula[i : j + 1])
                if num == 0:
                    raise FormulaError("count is zero", formula, i)
            elif char.islower():
                if not formula[i - 1].isupper():
                    raise FormulaError(f"unexpected character '{char}'", formula, i)
                ele = char
            elif char.isupper():
                ele = char + ele
                if num == 0:
                    num = 1
                if ele not in ELEMENTS:
                    raise FormulaError(f"unknown symbol '{ele}'", formula, i)
                iso = ""
                j = i
                while i and formula[i - 1].isdigit():
                    i -= 1
                    iso = formula[i] + iso
                if iso and i and not formula[i - 1] in "([{<":
                    i = j
                    iso = ""
                if iso:
                    iso = int(iso)
                    if iso not in ELEMENTS[ele].isotopes:
                        raise FormulaError(f"unknown isotope '{iso}{ele}'", formula, i)
                else:
                    iso = 0
                number = num * counts[level]
                if ele in elements:
                    item = elements[ele]
                    if iso in item:
                        item[iso] += number
                    else:
                        item[iso] = number
                else:
                    elements[ele] = {iso: number}
                ele = ""
                num = 0

        if num != 0:
            raise FormulaError("number preceding formula", formula, 0)

        if level != 0:
            raise FormulaError("missing opening parenthesis '([{<'", formula, 0)

        if not elements:
            raise FormulaError("invalid formula", formula, 0)

        return elements

    @lazyattr
    def charge(self):
        """Return formula charge.

        Examples
        --------
        >>> Formula("C8H14Br4+H+").charge
        1
        >>> Formula("C8H14Br4+-").charge
        0
        >>> Formula("C14H17N2O_-").charge
        -1
        >>> Formula("C56H75I4N13O2Pt2++").charge
        2
        >>> Formula("C56H75I4N13O2Pt2_2+").charge
        2

        """
        charge = 0
        m = re.search(r"\]{1,}([0-9]*)([+-]{1,})$", self._formula)
        if m:
            if m.groups()[0] == "":
                charge = int("%s1" % m.groups()[1])
            else:
                charge = int("%s%s" % (m.groups()[1], m.groups()[0]))
        return charge

    @lazyattr
    def formula(self):
        """Return formula string in Hill notation.

        Examples
        --------
        >>> Formula('BrC2H5').formula
        'C2H5Br'
        >>> Formula('HBr').formula
        'BrH'
        >>> Formula('[(CH3)3Si2]2NNa').formula
        'C6H18NNaSi4'

        """
        return from_elements(self._elements)

    @lazyattr
    def empirical(self):
        """Return empirical formula in Hill notation.

        The empirical formula has the simplest whole number ratio of atoms
        of each element present in formula.

        Examples
        --------
        >>> Formula('H2O').empirical
        'H2O'
        >>> Formula('S4').empirical
        'S'
        >>> Formula('C6H12O6').empirical
        'CH2O'

        """
        return from_elements(self._elements, self.gcd)

    @lazyattr
    def atoms(self):
        """Return number of atoms.

        Examples
        --------
        >>> Formula('CH3COOH').atoms
        8

        """
        return sum(sum(i.values()) for i in self._elements.values())

    @lazyattr
    def gcd(self):
        """Return greatest common divisor of element counts.

        Examples
        --------
        >>> Formula('H2').gcd
        2
        >>> Formula('H2O').gcd
        1
        >>> Formula('C6H12O6').gcd
        6

        """
        return gcd({list(i)[0] for i in (j.values() for j in self._elements.values())})

    @lazyattr
    def mz(self):
        """Return monoisotopic mass corrected by ion charge.

        Examples
        --------
        >>> def _(mass):
        ...    print(f'{mass:.4f}')
        >>> _(Formula('H').mz)
        1.0079
        >>> _(Formula('H+').mz)
        1.0074
        >>> _(Formula('SO4_2-').mz)
        48.0318

        """
        if self.charge != 0:
            return (self.isotope.mass - ELECTRON.mass * self.charge) / abs(self.charge)

        return 0

    @lazyattr
    def mass(self):
        """Return average relative molecular mass.

        Sums the relative atomic masses of all atoms in molecule.
        Equals the molar mass in g/mol, i.e. the mass of one mole of substance.

        Examples
        --------
        >>> Formula('C').mass
        12.01074
        >>> Formula('12C').mass
        12.0
        >>> print('{:.2f}'.format(Formula('C48H32AgCuO12P2Ru4').mass))
        1438.40

        """
        result = 0.0
        for symbol in self._elements:
            ele = ELEMENTS[symbol]
            for massnumber, count in self._elements[symbol].items():
                if massnumber:
                    result += ele.isotopes[massnumber].mass * count
                else:
                    result += ele.mass * count

        return result

    @lazyattr
    def isotope(self):
        """Return isotope composed of most abundant elemental isotopes.

        Examples
        --------
        >>> print(Formula('C').isotope.mass)
        12.0
        >>> Formula('13C').isotope.massnumber
        13
        >>> print(Formula('C48H32AgCuO12P2Ru4').isotope)
        1440, 1439.5890, 0.205075%

        """
        result = Isotope(charge=self.charge)
        for symbol in self._elements:
            ele = ELEMENTS[symbol]
            for massnumber, count in self._elements[symbol].items():
                if massnumber:
                    isotope = ele.isotopes[massnumber]
                else:
                    isotope = ele.isotopes[ele.nominalmass]
                result.mass += isotope.mass * count
                result.massnumber += isotope.massnumber * count
                result.abundance *= isotope.abundance**count

        return result

    def composition(self, isotopic=True):
        """Return elemental composition as Composition instance.

        Return type is tuple(tuple(symbol, count, mass, fraction), ).

        If isotopic is True, isotopes specified in the formula are listed
        separately, otherwise they are listed as part of an element.

        Examples
        --------
        >>> Formula('[12C]C').composition(False)
        (('C', 2, 24.01074, 1.0),)
        >>> for i in Formula('[12C]C').composition(True): print(i)
        ('C', 1, 12.01074, 0.5002236499166623)
        ('12C', 1, 12.0, 0.49977635008333776)

        """
        elements = self._elements
        result = []
        if isotopic:
            for symbol in hill_sorted(elements):
                ele = ELEMENTS[symbol]
                iso = elements[symbol]
                for massnumber in sorted(iso):
                    count = iso[massnumber]
                    if massnumber:
                        mass = ele.isotopes[massnumber].mass * count
                        symbol = f"{massnumber}{symbol}"
                    else:
                        mass = ele.mass * count
                    result.append((symbol, count, mass, mass / self.mass))
        else:
            for symbol in hill_sorted(elements):
                ele = ELEMENTS[symbol]
                mass = 0.0
                counter = 0
                for massnumber, count in elements[symbol].items():
                    counter += count
                    if massnumber:
                        mass += ele.isotopes[massnumber].mass * count
                    else:
                        mass += ele.mass * count
                result.append((symbol, counter, mass, mass / self.mass))
        return Composition(result)

    def spectrum(self, minfract=1e-9):
        """Return low resolution mass spectrum as Spectrum instance.

        Return type is dict{massnumber: list[mass, fraction]}.

        Calculated by combining the mass numbers of the elemental isotopes.
        """
        spectrum = {0: [0.0, 1.0]}
        elements = self._elements

        for symbol in elements:
            ele = ELEMENTS[symbol]
            for massnumber, count in elements[symbol].items():
                if massnumber:
                    # specific isotope
                    iso = ele.isotopes[massnumber]
                    for key in reversed(sorted(spectrum)):
                        t = spectrum[key]
                        del spectrum[key]
                        if t[1] < minfract:
                            continue
                        f = t[1]
                        m = t[0] + iso.mass * count
                        k = key + iso.massnumber * count
                        if k in spectrum:
                            s = spectrum[k]
                            s[0] += (s[1] * s[0] + f * m) / (s[1] + f)
                            s[1] += f
                        else:
                            spectrum[k] = [m, f]
                else:
                    # mixture of isotopes
                    isotopes = ele.isotopes.values()
                    for _ in range(count):
                        for key in reversed(sorted(spectrum)):
                            t = spectrum[key]
                            del spectrum[key]
                            if t[1] < minfract:
                                continue
                            for iso in isotopes:
                                f = t[1] * iso.abundance
                                m = t[0] + iso.mass
                                k = key + iso.massnumber
                                if k in spectrum:
                                    s = spectrum[k]
                                    s[0] = (s[1] * s[0] + f * m) / (s[1] + f)
                                    s[1] += f
                                else:
                                    spectrum[k] = [m, f]

        return Spectrum(spectrum)

    def mz_spectrum(self, minfract=1e-9, isotope_threshold=1e-3):
        """Return low resolution mz spectrum as Spectrum instance.

        Return type is dict{massnumber: list[mz, percentage_of_maximum]}.

        Examples
        --------
        >>> def _(spectrum):
        ...     for key, val in spectrum.items():
        ...         print(f'{key}, {val[0]:.6f}, {val[1]:.3f}%')
        >>> _(Formula("C16H31O2-").mz_spectrum())
        255, 255.232954, 100.000%
        256, 256.236371, 17.738%
        257, 257.239232, 1.891%
        258, 258.241960, 0.150%
        259, 259.244718, 0.009%
        >>> _(Formula("[C53H100NO6]+").mz_spectrum())
        846, 846.754516, 100.000%
        847, 847.757892, 59.067%
        848, 848.761101, 18.367%
        849, 849.764189, 3.981%
        850, 850.767191, 0.672%
        851, 851.770133, 0.094%
        852, 852.773030, 0.011%
        853, 853.775896, 0.001%
        """
        spectrum = self.spectrum(minfract=minfract)
        mz_spectrum = {}

        # Correct mass with charge
        for key, val in spectrum.items():
            percentage = val[1]
            if percentage >= isotope_threshold:
                mz = (
                    (val[0] - ELECTRON.mass * self.charge) / abs(self.charge)
                    if self.charge != 0
                    else val[0]
                )
                mz_spectrum[key] = [mz, percentage]

        return Spectrum(mz_spectrum)


class Spectrum(dict):
    """Mass distribution.

    Basic type is dict{bin: list[mass, fraction]}.
    Iterators over the dict are sorted by bin/mass.

    Examples
    --------
    >>> print(Spectrum({1: [1.078, 0.9999], 2: [2.014, 0.0001]}))
    Relative mass    Fraction %      Intensity
    1.0780000         99.990000     100.000000
    2.0140000          0.010000       0.010001

    """

    def __init__(self, *args, **kwds):
        dict.__init__(self, *args, **kwds)
        self._sorted_keys = sorted(dict.keys(self))

    def __iter__(self):
        return iter(self._sorted_keys)

    def keys(self):
        return iter(self._sorted_keys)

    def values(self):
        return (self[key] for key in self._sorted_keys)

    def items(self):
        return ((key, self[key]) for key in self._sorted_keys)

    @lazyattr
    def range(self):
        """Return smallest and largest bin number."""
        return min(dict.keys(self)), max(dict.keys(self))

    @lazyattr
    def peak(self):
        """Return most abundant mass and fraction."""
        mass = 0.0
        fraction = 0.0
        for m, f in dict.values(self):
            if f > fraction:
                fraction = f
                mass = m
        return mass, fraction

    @lazyattr
    def mean(self):
        """Return mean of all masses in spectrum."""
        return sum((mass * fraction) for mass, fraction in dict.values(self))

    def __str__(self):
        if len(self) == 0:
            return ""
        result = ["Relative mass    Fraction %      Intensity"]
        prec = precision_digits(self.peak[0], 9)
        norm = 100.0 / self.peak[1]
        for mass, fraction in self.values():
            result.append(
                "{:<13.{}f}   {:11.6f}   {:12.6f}".format(
                    mass, prec, fraction * 100.0, fraction * norm
                )
            )
        return "\n".join(result)


class Composition(tuple):
    """Elemental composition.

    Basic type is tuple(tuple(symbol, count, mass, fraction), ).

    Examples
    --------
    >>> print(Composition((('2H', 2, 4.028, 0.201), ('O', 1, 15.999, 0.799))))
    Element  Number  Relative mass  Fraction %
    2H            2       4.028000     20.1000
    O             1      15.999000     79.9000
    Total:        3      20.027000    100.0000

    """

    @lazyattr
    def total(self):
        """Return sums of counts, masses, and fractions."""
        result = [0, 0.0, 0.0]
        for item in self:
            result[0] += item[1]
            result[1] += item[2]
            result[2] += item[3]
        return tuple(result)

    def __str__(self):
        if len(self) == 0:
            return ""
        prec = precision_digits(self.total[1], 9)
        result = ["Element  Number  Relative mass  Fraction %"]
        for symbol, count, mass, fraction in self:
            result.append(
                "{:<6s} {:8}  {:13.{}f} {:11.4f}".format(
                    symbol, count, mass, prec, fraction * 100
                )
            )
        if len(self) > 1:
            count, mass, fraction = self.total
            result.append(
                "{:<6s} {:8}  {:13.{}f} {:11.4f}".format(
                    "Total:", count, mass, prec, fraction * 100
                )
            )
        return "\n".join(result)


class FormulaError(Exception):
    """Custom exception to report errors in the Formula object."""

    def __init__(self, msg, formula="", pos=-1):
        self.position = pos
        self.message = msg
        self.formula = formula
        Exception.__init__(self, msg, formula, pos)

    def __str__(self):
        if self.position < 0:
            return str(self.message)
        return f"{self.message}\n{self.formula}\n{'.' * self.position}^"


def from_string(formula, groups=None):
    """Return formula string from user input string.

    Return string should be composed of chemical elements/isotopes,
    parentheses, and numbers only. Raise FormulaError on errors.

    Supports simple, non-nested, arithmetic (+ and *), abbreviations of
    common chemical groups, peptides, oligos, and mass fractions.
    """
    try:
        formula = formula.strip().replace(" ", "")
    except AttributeError as exc:
        raise FormulaError("not a string") from exc

    # abbreviations of common chemical groups
    if groups is None:
        groups = GROUPS
    if groups:
        for grp in reversed(sorted(groups)):
            formula = formula.replace(grp, f"({groups[grp]})")

    # Charge
    charge = 0
    m = re.search("([_]{1,})([0-9]{1,})([+-]{1,})$", formula)
    if m:
        # Search for multi-charged (e.g. *_2-)
        if m.groups()[1] == "":
            # Do we ever end up in here?
            charge = int("%s1" % m.groups()[2])
        else:
            charge = int("%s%s" % (m.groups()[2], m.groups()[1]))
        if m.groups()[0] == "_":
            formula = formula.split("_")[0]
        elif m.groups()[0] == "":
            formula = formula.strip(m.groups()[2])
        elif m.groups()[0] == "]":
            formula = formula.split("]")[0] + "]"
    else:
        # Search for singly charged (e.g. *_- or *-)
        m = re.search(r"([\]_]?)([+-]{1,})$", formula)
        charge = 0
        if m:
            for char in m.groups()[1]:
                if char == "+":
                    charge += 1
                elif char == "-":
                    charge -= 1
            if m.groups()[0] == "_":
                formula = formula.split("_")[0]
            elif m.groups()[0] == "":
                formula = formula.strip(m.groups()[1])
            elif m.groups()[0] == "]":
                formula = formula.split("]")[0] + "]"
    if formula.startswith("[") and formula.endswith("]"):
        formula = formula.strip("[").strip("]")

    # arithmetic
    formula = formula.replace(".", "+")
    if "+" in formula:
        for match in re.findall(r"(?:\+|^)((\d+)\*?(.*?))(?:(?=\+)|$)", formula):
            formula = formula.replace(match[0], f"({match[2]}){match[1]}")
        formula = formula.replace("+", "")
    if "-" in formula:
        # Check for parenthesis
        for match in re.findall(r"([(]{1,})([\w]*)([-]{1,})([\w]*)([)]{1,})", formula):
            a, b = match[1], match[3]
            sub = Formula(a) - Formula(b)
            formula = formula.replace("".join(match), sub.formula)

    # Charge
    if charge != 0:
        formula = "[%s]%s%s" % (
            formula,
            abs(charge) if abs(charge) > 1 else "",
            "+" if charge > 0 else "-",
        )

    return formula


def from_elements(elements, divisor=1, *fmt):
    """Return formula string in Hill notation from elements dict.

    Examples
    --------
    >>> from_elements({'C': {0: 4, 12: 2}}, 2)
    'C2[12C]'
    >>> from_elements({'C': {0: 4, 12: 2}}, 2, '{}', '{}<sub>{}</sub>',
    ...     '<sup>{}</sup>{}', '<sup>{}</sup>{}<sub>{}</sub>')
    'C<sub>2</sub><sup>12</sup>C'

    """
    if not fmt:
        fmt = ("{}", "{}{}", "[{}{}]", "[{}{}]{}")
    formula = []
    for symbol in hill_sorted(elements):
        isotopes = elements[symbol]
        for massnumber in sorted(isotopes):
            count = isotopes[massnumber] // divisor
            if massnumber:
                if count == 1:
                    formula.append(fmt[2].format(massnumber, symbol))
                else:
                    formula.append(fmt[3].format(massnumber, symbol, count))
            else:
                if count == 1:
                    formula.append(fmt[0].format(symbol))
                else:
                    formula.append(fmt[1].format(symbol, count))
    return "".join(formula)


def from_sequence(sequence, items):
    """Translate sequence using items dict and return histogram of items in
    translated sequence as formula string.

    Raise KeyError if a sequence item is not in items.

    Examples
    --------
    >>> from_sequence('A', {'A': 'B'})
    '(B)'
    >>> from_sequence('AA', {'A': 'B'})
    '(B)2'

    """
    counts = {key: 0 for key in items}
    for item in sequence:
        counts[item] += 1
    formula = []
    for key in sorted(items):
        num = counts[key]
        if num == 1:
            formula.append(f"({items[key]})")
        elif num:
            formula.append(f"({items[key]}){num}")
    return "".join(formula)


def hill_sorted(symbols):
    """Return iterator over element symbols in order of Hill notation.

    Examples
    --------
    >>> for i in hill_sorted('HCO'): print(i, end='')
    CHO

    """
    symbols = set(symbols)
    if "C" in symbols:
        symbols.remove("C")
        yield "C"
        if "H" in symbols:
            symbols.remove("H")
            yield "H"
    yield from sorted(symbols)


def gcd(numbers):
    """Return greatest common divisor of integer numbers.

    Using Euclid's algorithm.

    Examples
    --------
    >>> gcd([4])
    4
    >>> gcd([3, 6])
    3
    >>> gcd([6, 7])
    1

    """

    def _gcd(a, b):
        """Return greatest common divisor of two integer numbers."""
        while b:
            a, b = b, a % b
        return a

    return reduce(_gcd, numbers)


def precision_digits(f, width):
    """Return number of digits after decimal point to print f in width chars.

    Examples
    --------
    >>> precision_digits(-0.12345678, 5)
    2
    >>> precision_digits(1.23456789, 5)
    3
    >>> precision_digits(12.3456789, 5)
    2
    >>> precision_digits(12345.6789, 5)
    1

    """
    precision = math.log(abs(f), 10)
    if precision < 0:
        precision = 0
    precision = width - int(math.floor(precision))
    precision -= 3 if f < 0 else 2  # sign and decimal point
    if precision < 1:
        precision = 1
    return precision


# Common chemical groups
GROUPS = {
    "Abu": "C4H7NO",
    "Acet": "C2H3O",
    "Acm": "C3H6NO",
    "Adao": "C10H15O",
    "Aib": "C4H7NO",
    "Ala": "C3H5NO",
    "Arg": "C6H12N4O",
    "Argp": "C6H11N4O",
    "Asn": "C4H6N2O2",
    "Asnp": "C4H5N2O2",
    "Asp": "C4H5NO3",
    "Aspp": "C4H4NO3",
    "Asu": "C8H13NO3",
    "Asup": "C8H12NO3",
    "Boc": "C5H9O2",
    "Bom": "C8H9O",
    "Bpy": "C10H8N2",  # Bipyridine
    "Brz": "C8H6BrO2",
    "Bu": "C4H9",
    "Bum": "C5H11O",
    "Bz": "C7H5O",
    "Bzl": "C7H7",
    "Bzlo": "C7H7O",
    "Cha": "C9H15NO",
    "Chxo": "C6H11O",
    "Cit": "C6H11N3O2",
    "Citp": "C6H10N3O2",
    "Clz": "C8H6ClO2",
    "Cp": "C5H5",
    "Cy": "C6H11",
    "Cys": "C3H5NOS",
    "Cysp": "C3H4NOS",
    "Dde": "C10H13O2",
    "Dnp": "C6H3N2O4",
    "Et": "C2H5",
    "Fmoc": "C15H11O2",
    "For": "CHO",
    "Gln": "C5H8N2O2",
    "Glnp": "C5H7N2O2",
    "Glp": "C5H5NO2",
    "Glu": "C5H7NO3",
    "Glup": "C5H6NO3",
    "Gly": "C2H3NO",
    "Hci": "C7H13N3O2",
    "Hcip": "C7H12N3O2",
    "His": "C6H7N3O",
    "Hisp": "C6H6N3O",
    "Hser": "C4H7NO2",
    "Hserp": "C4H6NO2",
    "Hx": "C6H11",
    "Hyp": "C5H7NO2",
    "Hypp": "C5H6NO2",
    "Ile": "C6H11NO",
    "Ivdde": "C14H21O2",
    "Leu": "C6H11NO",
    "Lys": "C6H12N2O",
    "Lysp": "C6H11N2O",
    "Mbh": "C15H15O2",
    "Me": "CH3",
    "Mebzl": "C8H9",
    "Meobzl": "C8H9O",
    "Met": "C5H9NOS",
    "Mmt": "C20H17O",
    "Mtc": "C14H19O3S",
    "Mtr": "C10H13O3S",
    "Mts": "C9H11O2S",
    "Mtt": "C20H17",
    "Nle": "C6H11NO",
    "Npys": "C5H3N2O2S",
    "Nva": "C5H9NO",
    "Odmab": "C20H26NO3",
    "Orn": "C5H10N2O",
    "Ornp": "C5H9N2O",
    "Pbf": "C13H17O3S",
    "Pen": "C5H9NOS",
    "Penp": "C5H8NOS",
    "Ph": "C6H5",
    "Phe": "C9H9NO",
    "Phepcl": "C9H8ClNO",
    "Phg": "C8H7NO",
    "Pmc": "C14H19O3S",
    "Ppa": "C8H7O2",
    "Pro": "C5H7NO",
    "Prop": "C3H7",
    "Py": "C5H5N",
    "Pyr": "C5H5NO2",
    "Sar": "C3H5NO",
    "Ser": "C3H5NO2",
    "Serp": "C3H4NO2",
    "Sta": "C8H15NO2",
    "Stap": "C8H14NO2",
    "Tacm": "C6H12NO",
    "Tbdms": "C6H15Si",
    "Tbu": "C4H9",
    "Tbuo": "C4H9O",
    "Tbuthio": "C4H9S",
    "Tfa": "C2F3O",
    "Thi": "C7H7NOS",
    "Thr": "C4H7NO2",
    "Thrp": "C4H6NO2",
    "Tips": "C9H21Si",
    "Tms": "C3H9Si",
    "Tos": "C7H7O2S",
    "Trp": "C11H10N2O",
    "Trpp": "C11H9N2O",
    "Trt": "C19H15",
    "Tyr": "C9H9NO2",
    "Tyrp": "C9H8NO2",
    "Val": "C5H9NO",
    "Valoh": "C5H9NO2",
    "Valohp": "C5H8NO2",
    "Xan": "C13H9O",
}


def test(verbose=False):
    """Test the module and the examples in docstrings."""
    import doctest

    doctest.testmod(verbose=verbose)

    # these formulas should pass
    for data in [
        ("".join(e.symbol for e in ELEMENTS), "", 14693.181589000998),
        ("12C", "[12C]", 12.0),
        ("12CC", "C[12C]", 24.0107),
        ("Co(Bpy)(CO)4", "", 327.16),
        ("CH3CH2Cl", "C2H5Cl", 64.5147),
        ("C1000H1000", "CH", 13018.68),
        ("Ru2(CO)8", "C4O4Ru", 426.2232),
        ("RuClH(CO)(PPh3)3", "C55H46ClOP3Ru", 952.41392),
        ("PhSiMe3", "C9H14Si", 150.29566),
        ("Ph(CO)C(CH3)3", "C11H14O", 162.23156),
        ("HGlyGluTyrOH", "C16H21N3O7", 367.35864),
        ("[13C]Cl4", "[13C]Cl4", 154.8153),
        ("C5(PhBu(EtCHBr)2)3", "C53H78Br6", 1194.626),
        ("AgCuRu4(H)2[CO]12{PPh3}2", "C48H32AgCuO12P2Ru4", 1438.4022),
        ("PhNH2.HCl", "C6H8ClN", 129.5892),
        ("NH3.BF3", "BF3H3N", 84.8357),
        ("CuSO4.5H2O", "CuH10O9S", 249.68),
    ]:
        if verbose:
            runtime.logger.info(f"Trying Formula('{data[0]}') ...", end="")
        try:
            f = Formula(data[0])
            f.empirical
            f.mass
            f.spectrum
        except FormulaError as exc:
            runtime.logger.error(exc)
            continue
        if data[1] and f.empirical != data[1]:
            runtime.logger.error(
                "Failure for {}:\n    Expected '{}', got '{}':".format(
                    data[0], data[1], f.empirical
                )
            )
            continue
        if data[2] and abs(f.mass - data[2]) > 0.1:
            runtime.logger.error(
                "Failure for {}:\n    Expected {}, got {}".format(
                    data[0], data[2], f.mass
                )
            )
            continue
        if verbose:
            runtime.logger.info("ok")

    # these formulas are expected to fail
    for data in [
        "",
        "()",
        "2",
        "a",
        "(a)",
        "C:H",
        "H:",
        "C[H",
        "H)2",
        "A",
        "Aa",
        "2lC",
        "1C",
        "[11C]",
        "H0",
        "()0",
        "(H)0C",
        "Ox: 0.26, 30Si: 0.74",
    ]:
        if verbose:
            runtime.logger.info(f"Trying Formula('{data}') ...", end="")
        try:
            f = Formula(data).empirical
        except FormulaError as exc:
            if verbose:
                runtime.logger.error(f"ok\nExpected error: {exc}")
        else:
            runtime.logger.error(
                f"Failure expected for '{data}', got '{Formula(data).formula}'"
            )


def main(argv=None):
    """Command line usage main function."""
    if argv is None:
        argv = sys.argv

    import optparse

    def search_doc(r, d):
        return re.search(r, __doc__).group(1) if __doc__ else d

    parser = optparse.OptionParser(
        usage="usage: %prog [options] formula",
        description=search_doc("\n\n([^|]*?)\n\n", ""),
        version="%prog {}".format(search_doc(":Version: (.*)", "Unknown")),
        prog="molmass",
    )
    opt = parser.add_option

    opt(
        "--test",
        dest="test",
        action="store_true",
        default=False,
        help="test the module",
    )
    opt("-v", "--verbose", dest="verbose", action="store_true", default=False)

    settings, formula = parser.parse_args()

    if settings.test:
        test(settings.verbose)
        return 0
    if formula:
        formula = "".join(formula)
    else:
        parser.error("no formula specified")

    try:
        results = analyze(formula)
    except Exception as exc:
        runtime.logger.error("\nError: \n  ", exc, sep="")
        raise exc
    else:
        runtime.logger.info("\n", results, sep="")


if __name__ == "__main__":
    from pprint import pprint  # noqa: used by doctest

    sys.exit(main())
