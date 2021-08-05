# -*- coding: utf-8 -*-
"""Chemistry functions

Created on Tue Jan  7 10:28:20 2020
"""

import numpy as np

from karsatof.lib.TwTool import (
                        TwGetMoleculeMass,
                        TwGetIsotopePattern,
                        TwDecomposeMass,
                        TwGetComposition
                        )

from ctypes import create_string_buffer


def get_exact_mass(molComp):
    """Function to calculate the exact mass of a molecule with the given 
       elemental composition
        
    Parameters
    ----------
    molComp : str
        Molecular composition for which to calculate the mass
    
    Returns
    -------
    mass : double
        mass of the given composition
        
    Raises
    -------
    ValueError
        If the calculation fails
    """
        
    mass = np.zeros((1,))
    if TwGetMoleculeMass(molComp.encode(), mass) == 4:
        return np.asscalar(mass)
    else:
        raise ValueError
        
        
def get_exact_isotope_masses(molComp, abu_limit=0):
    """Function to calculate the masses and abundances of a number of isotopes
       of a given elemental composition
        
    Parameters
    ----------
    molComp : str
        Molecular composition for which to calculate the mass
    abu_limit : float
        Isotope masses with relative abundance greater than this
        will be returned, should be in range [0, 1]
        
    Returns
    -------
    masses : array
        array of isotope masses for the given composition
    abundances : array
        array of isotope abundances for the given composition
        
    Raises
    -------
    ValueError
        If the calculation fails
    """
    
    # Get number of isotopes within abundance limit
    nbrIsotopes = np.zeros((1,), dtype=np.int)
    if TwGetIsotopePattern(molComp.encode(),
                           abu_limit,
                           nbrIsotopes,
                           None,
                           None) == 9:
        masses = np.zeros((nbrIsotopes[0],))
        abundances = np.zeros((nbrIsotopes[0],))
    else:
        raise ValueError
    # Get isotope masses and abundances
    if TwGetIsotopePattern(molComp.encode(),
                           abu_limit,
                           nbrIsotopes,
                           masses,
                           abundances) == 4:
        # Scale
        abundances /= np.sum(abundances)
        # Sort
        sind = np.flip( np.argsort(abundances) )
        masses = masses[sind]
        abundances = abundances[sind]
    else:
        raise ValueError
    return masses, abundances


def guess_composition(target_mz,
                      el_filter,
                      tolerance=10e-6):
    """Function to guess the elemental composition based on
       mass and a list of allowed elements and their numbers and ratios
        
    Parameters
    ----------
    target_mz : double
        Mass for which to guess the elemental composition
    elements : list
        List of elements allowed in the composition
    num_filter : list
        List of 2-tuples per element, with min and max allowed number
    ratio_filter : list
        List of 4-tuples, with indices of two elements, and 
        min and max allowed ratio for those two
    tolerance : double
        Maximum allowed relative m/z error
        
    Returns
    -------
    formulae : list
        List of elemental compositions within set mass tolerance
        
    TODO: TO BE REVIEWED
    """
    
    def parse_filter(el_filter):
        elements = []
        num_filter = []
        ratio_filter = []
        for row in el_filter:
            if not ':' in row['el']:
                elements.append(row['el'])
                num_filter.append((row['min'], row['max']))
        for row in el_filter:
            if ':' in row['el']:
                els = row['el'].split(':')
                el1 = elements.index(els[0])
                el2 = elements.index(els[1])
                ratio_filter.append((el1, el2, row['min'], row['max']))
        return elements, num_filter, ratio_filter

    elements, num_filter, ratio_filter = parse_filter(el_filter)

    tolerance *= target_mz
    nbrAtoms = len(elements)
    m = np.zeros((1,))
    atomMass = np.array([m[0] for el in elements 
                         if TwGetMoleculeMass(el.encode(), m)==4], 
                         dtype=np.double)
    atomLabel = '\0'.join(elements)
    # Filters
    if len(ratio_filter) > 0:
        nbrFilters = len(num_filter) + len(ratio_filter)
        elementIndex1 = np.array(list(range(len(elements))) + 
                                 list(list(zip(*ratio_filter))[0]),
                                 dtype=np.int) # Element index for count filters, first element index for ratio filters.
        elementIndex2 = np.array([-1]*len(elements) +
                                 list(list(zip(*ratio_filter))[1]),
                                 dtype=np.int) # -1 for count filters, second element for ratio filters.
        filterMinVal = np.array(list(list(zip(*num_filter))[0]) +
                                list(list(zip(*ratio_filter))[2]),
                                dtype=np.double)
        filterMaxVal = np.array(list(list(zip(*num_filter))[1]) +
                                list(list(zip(*ratio_filter))[3]),
                                dtype=np.double)
    else:
        nbrFilters = len(num_filter) + len(ratio_filter)
        elementIndex1 = np.array(range(len(elements)), dtype=np.int) # Element index for count filters, first element index for ratio filters.
        elementIndex2 = np.array([-1]*len(elements), dtype=np.int) # -1 for count filters, second element for ratio filters.
        filterMinVal = np.array(list(zip(*num_filter))[0], dtype=np.double)
        filterMaxVal = np.array(list(zip(*num_filter))[1], dtype=np.double)
    nbrCompomers = np.array([0], dtype=np.int)
    # Guess
    TwDecomposeMass(target_mz, tolerance, nbrAtoms, atomMass, atomLabel.encode(), 
                    nbrFilters, elementIndex1, elementIndex2, filterMinVal, 
                    filterMaxVal, nbrCompomers)
    # Read results
    formulae = []
    diffs = []
    for i in range(nbrCompomers[0]):
        sumFormulaLength = np.array([256], dtype=np.int)
        sumFormula = create_string_buffer(b'', sumFormulaLength[0])
        mass = np.array([0], dtype=np.double)
        massError = np.array([0], dtype=np.double)
        TwGetComposition(i, sumFormula, sumFormulaLength, mass, massError)
        formula = np.asarray(sumFormula).view('S256').ravel()
        formulae.append(formula[0])
        diffs.append(massError.item())
    return formulae, diffs