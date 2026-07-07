import { describe, it, expect } from 'vitest'

import {
  isValidChemicalFormula,
  isSameCompound,
  findExistingCompound,
  formatIsotopeFormula
} from '@/lib/chem'

describe('isValidChemicalFormula', () => {
  it.each(['C6H12O6', 'Ca(OH)2', '(NH4)2SO4', '()', 'H^NO3', 'H2SO4', 'C'])(
    'accepts %s',
    (formula) => {
      expect(isValidChemicalFormula(formula)).toBe(true)
    }
  )

  it.each(['invalid123', 'h2o', '123', 'C6H12O6-', '', null, undefined])(
    'rejects %s',
    (formula) => {
      expect(isValidChemicalFormula(formula)).toBe(false)
    }
  )

  it('normalizes surrounding whitespace before validating', () => {
    expect(isValidChemicalFormula('  C6H12O6  ')).toBe(true)
  })
})

describe('isSameCompound', () => {
  const glucose = { target_compound_formula: 'C6H12O6', cas_number: '50-99-7' }

  it('matches by normalized CAS number', () => {
    const other = { target_compound_formula: 'C2H6O', cas_number: ' 50-99-7 ' }
    expect(isSameCompound(glucose, other)).toBe(true)
  })

  it('matches by case-insensitive formula', () => {
    const other = { target_compound_formula: ' c6h12o6 ' }
    expect(isSameCompound(glucose, other)).toBe(true)
  })

  it('does not match different compounds', () => {
    const other = { target_compound_formula: 'C2H6O', cas_number: '64-17-5' }
    expect(isSameCompound(glucose, other)).toBe(false)
  })

  it('never matches when a formula is missing or blank', () => {
    expect(isSameCompound(glucose, { cas_number: '50-99-7' })).toBe(false)
    expect(isSameCompound(glucose, { target_compound_formula: '  ' })).toBe(false)
    expect(isSameCompound(glucose, null)).toBe(false)
  })
})

describe('findExistingCompound', () => {
  const list = [
    { target_compound_formula: 'C6H12O6', cas_number: '50-99-7' },
    { target_compound_formula: 'C2H6O', cas_number: '64-17-5' }
  ]

  it('finds a compound by formula', () => {
    expect(findExistingCompound(list, { target_compound_formula: 'c2h6o' })).toBe(list[1])
  })

  it('returns null when the search compound has no formula', () => {
    expect(findExistingCompound(list, { cas_number: '50-99-7' })).toBe(null)
    expect(findExistingCompound(list, null)).toBe(null)
  })

  it('returns undefined when nothing matches', () => {
    expect(findExistingCompound(list, { target_compound_formula: 'CH4' })).toBeUndefined()
  })
})

describe('formatIsotopeFormula', () => {
  // Cases documented in the function docstring.
  it.each([
    ['C3H6O3', 'M0'],
    ['[13C]C2H6O3', '[13C]'],
    ['[13C]C2[2H]H5O3', '[13C][2H]'],
    ['[13C]2CH6O3', '[13C]2'],
    ['[13C]C2H6O3/C3H6[18O]O2', '[13C]/[18O]']
  ])('formats %s as %s', (formula, expected) => {
    expect(formatIsotopeFormula(formula)).toBe(expected)
  })

  it('returns an empty string for empty input', () => {
    expect(formatIsotopeFormula('')).toBe('')
    expect(formatIsotopeFormula(null)).toBe('')
  })
})
