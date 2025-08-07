import { norm } from '@/lib/utils'

/**
 * Validates chemical formula format
 * Supports standard chemical notation including parentheses and empty parentheses ()
 *
 * @param {string} formula - Chemical formula to validate
 * @returns {boolean} True if valid chemical formula
 *
 * Examples:
 * - "C6H12O6" ✓
 * - "Ca(OH)2" ✓
 * - "(NH4)2SO4" ✓
 * - "()" ✓ (empty parentheses allowed)
 * - "invalid123" ✗
 */
export function isValidChemicalFormula(formula) {
  if (!formula) return false
  const normalized = norm(formula)

  // Allow empty parentheses () as valid
  if (normalized === '()') return true

  // Standard chemical formula regex
  const regex = /^(?:[A-Z][a-z]?\d*|\([^()]*(?:\(.*\))?[^()]*\)\d+)+$/
  return regex.test(normalized)
  // See:
  //   Debugger: https://regex101.com/r/Mbjq8C/1
  //   Inspiration: https://stackoverflow.com/questions/23602175/regex-for-parsing-chemical-formulas#23602425
}

/**
 * Finds existing compound in database using backend matching logic
 * Matches by CAS number OR (name AND formula) combination
 *
 * @param {Array} compoundList - List of existing compounds to search in
 * @param {Object} searchCompound - Compound to search for with properties:
 *   - target_compound_formula: Chemical formula
 *   - target_compound_name: Compound name
 *   - cas_number: CAS registry number
 * @returns {Object|null} Existing compound if found, null otherwise
 */
export function findExistingCompound(compoundList, searchCompound) {
  if (!searchCompound?.target_compound_formula?.trim()) return null

  return compoundList.find((comp) => {
    const casMatch =
      searchCompound.cas_number &&
      comp.cas_number &&
      norm(comp.cas_number) === norm(searchCompound.cas_number)

    const nameFormulaMatch =
      norm(comp.target_compound_formula, true) ===
        norm(searchCompound.target_compound_formula, true) &&
      norm(comp.target_compound_name, true) === norm(searchCompound.target_compound_name, true)

    return casMatch || nameFormulaMatch
  })
}
