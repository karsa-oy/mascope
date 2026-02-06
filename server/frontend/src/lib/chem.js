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
 * - "H^NO3" ✓ (custom element denoted by caret)
 * - "invalid123" ✗
 */
export function isValidChemicalFormula(formula) {
  if (!formula) return false
  const normalized = norm(formula)

  // Allow empty parentheses () as valid
  if (normalized === '()') return true

  // Chemical formula regex, allows caret (^) prefix for custom elements (e.g. ^N) and parenthesis groups as part of the formula
  const regex = /^(?:\^?[A-Z][a-z]?\d*|\([^()]+\)\d*)+$/
  return regex.test(normalized)
  // See:
  //   Debugger: https://regex101.com/r/Mbjq8C/1
  //   Inspiration: https://stackoverflow.com/questions/23602175/regex-for-parsing-chemical-formulas#23602425
}

/**
 * Checks if two compounds are the same using matching by CAS number OR (name AND formula) combination
 *
 * @param {Object} compound1 - First compound to compare
 * @param {Object} compound2 - Second compound to compare
 * @returns {boolean} True if compounds match by CAS OR (name + formula)
 */
export function isSameCompound(compound1, compound2) {
  if (!compound1?.target_compound_formula?.trim() || !compound2?.target_compound_formula?.trim()) {
    return false
  }

  const casMatch =
    compound1.cas_number &&
    compound2.cas_number &&
    norm(compound1.cas_number) === norm(compound2.cas_number)

  const nameFormulaMatch =
    norm(compound1.target_compound_formula, true) ===
      norm(compound2.target_compound_formula, true) &&
    norm(compound1.target_compound_name, true) === norm(compound2.target_compound_name, true)

  return casMatch || nameFormulaMatch
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

  return compoundList.find((comp) => isSameCompound(comp, searchCompound))
}

/**
 * Formats isotope formulae by extracting isotope specifications
 * Returns "M0" for main isotope (no brackets) or all isotope bracketed patterns with their counts and forward slashes
 *
 * @param {string} formula - Chemical formula potentially containing isotope specifications in brackets
 * @returns {string} Formatted isotope string
 *
 * Examples:
 * - "C3H6O3" -> "M0" (no isotopes)
 * - "[13C]C2H6O3" -> "[13C]"
 * - "[13C]C2[2H]H5O3" -> "[13C][2H]"
 * - "[13C]2CH6O3" -> "[13C]2"
 * - "[13C]C2H6O3/C3H6[18O]O2" -> "[13C]/[18O]"
 */
export function formatIsotopeFormula(formula) {
  if (!formula) return ''

  // Match all bracket pairs with optional trailing digits and forward slashes: [content]digits or /
  const matches = formula.match(/\[[^\]]+\]\d*|\//g)

  return matches ? matches.join('') : 'M0'
}
