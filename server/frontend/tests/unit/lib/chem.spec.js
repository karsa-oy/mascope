import { describe, it, expect } from 'vitest'

import {
  isValidChemicalFormula,
  isSameCompound,
  findExistingCompound,
  formatIsotopeFormula,
  parseCompoundPaste,
  validateCompoundPaste
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

describe('parseCompoundPaste', () => {
  it('maps a single column to formulas only', () => {
    expect(parseCompoundPaste('H2O\nC6H12O6')).toEqual([
      { target_compound_formula: 'H2O' },
      { target_compound_formula: 'C6H12O6' }
    ])
  })

  it('handles Windows line endings and a trailing newline', () => {
    expect(parseCompoundPaste('H2O\r\nCO2\r\n')).toEqual([
      { target_compound_formula: 'H2O' },
      { target_compound_formula: 'CO2' }
    ])
  })

  it('drops a header cell from a single-column paste', () => {
    expect(parseCompoundPaste('Formula\nH2O')).toEqual([{ target_compound_formula: 'H2O' }])
  })

  it('keeps a lone single cell as-is for validation to judge', () => {
    expect(parseCompoundPaste('Formula')).toEqual([{ target_compound_formula: 'Formula' }])
  })

  it('maps two columns to name and formula', () => {
    expect(parseCompoundPaste('Water\tH2O')).toEqual([
      { target_compound_name: 'Water', target_compound_formula: 'H2O' }
    ])
  })

  it('maps three columns to name, formula and CAS number', () => {
    expect(parseCompoundPaste('Water\tH2O\t7732-18-5')).toEqual([
      { target_compound_name: 'Water', target_compound_formula: 'H2O', cas_number: '7732-18-5' }
    ])
  })
})

describe('validateCompoundPaste', () => {
  it('rejects empty or missing data', () => {
    expect(validateCompoundPaste(null).valid).toBe(false)
    expect(validateCompoundPaste([]).valid).toBe(false)
    expect(validateCompoundPaste([null]).valid).toBe(false)
  })

  it('accepts a formula-only column', () => {
    const result = validateCompoundPaste([
      { target_compound_formula: 'H2O' },
      { target_compound_formula: 'C6H12O6' }
    ])
    expect(result.valid).toBe(true)
    expect(result.message).toBe('Pasted 2 compounds')
  })

  it('accepts a single pasted formula cell', () => {
    const result = validateCompoundPaste([{ target_compound_formula: 'H2O' }])
    expect(result.valid).toBe(true)
    expect(result.message).toBe('Pasted 1 compound')
  })

  it('rejects a single column that does not contain formulas', () => {
    const result = validateCompoundPaste([
      { target_compound_formula: 'Water' },
      { target_compound_formula: 'Glucose' }
    ])
    expect(result.valid).toBe(false)
    expect(result.message).toContain('not a valid chemical formula')
  })

  it('accepts name and formula columns without formula syntax checks', () => {
    const result = validateCompoundPaste([
      { target_compound_name: 'Water', target_compound_formula: 'H2O' }
    ])
    expect(result.valid).toBe(true)
  })

  it('rejects rows missing a formula', () => {
    const result = validateCompoundPaste([
      { target_compound_name: 'Water', target_compound_formula: 'H2O' },
      { target_compound_name: 'Glucose', target_compound_formula: '' }
    ])
    expect(result.valid).toBe(false)
    expect(result.message).toBe('Some rows are missing a formula, which is required')
  })

  it('rejects more than three columns', () => {
    const result = validateCompoundPaste([
      { a: '1', b: '2', c: '3', d: '4' } // 4 columns
    ])
    expect(result.valid).toBe(false)
    expect(result.message).toContain('1 to 3 are expected')
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
