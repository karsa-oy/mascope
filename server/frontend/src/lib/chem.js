import { norm } from '@/lib/utils'
import { fromSpreadsheet } from '@/lib/table'

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
 * Checks if two compounds are the same using matching by CAS number OR formula
 *
 * @param {Object} compound1 - First compound to compare
 * @param {Object} compound2 - Second compound to compare
 * @returns {boolean} True if compounds match by CAS OR formula
 */
export function isSameCompound(compound1, compound2) {
  if (!compound1?.target_compound_formula?.trim() || !compound2?.target_compound_formula?.trim()) {
    return false
  }

  const casMatch =
    compound1.cas_number &&
    compound2.cas_number &&
    norm(compound1.cas_number) === norm(compound2.cas_number)

  const formulaMatch =
    norm(compound1.target_compound_formula, true) === norm(compound2.target_compound_formula, true)

  return casMatch || formulaMatch
}

/**
 * Finds existing compound in database using backend matching logic
 * Matches by CAS number OR formula
 *
 * @param {Array} compoundList - List of existing compounds to search in
 * @param {Object} searchCompound - Compound to search for with properties:
 *   - target_compound_formula: Chemical formula
 *   - cas_number: CAS registry number
 * @returns {Object|null} Existing compound if found, null otherwise
 */
export function findExistingCompound(compoundList, searchCompound) {
  if (!searchCompound?.target_compound_formula?.trim()) return null

  return compoundList.find((comp) => isSameCompound(comp, searchCompound))
}

/**
 * Parses spreadsheet cells pasted as target compounds.
 *
 * The column layout is inferred from the number of pasted columns:
 * - 1 column:  formula
 * - 2 columns: name, formula
 * - 3 columns: name, formula, CAS number
 *
 * A single-column paste may start with a header cell (e.g. "Formula"); it is
 * dropped when it is not a valid formula but the row below it is.
 *
 * @param {string} text - Raw clipboard text (tab-separated cells)
 * @returns {Array<Object>} Parsed compound rows
 */
export function parseCompoundPaste(text) {
  const lines = text.split('\n').filter((line) => line.trim().length)
  const cols = lines[0] ? lines[0].split('\t').length : 0
  const fields =
    cols === 1
      ? ['target_compound_formula']
      : ['target_compound_name', 'target_compound_formula', 'cas_number']
  const { rows } = fromSpreadsheet(text, fields)
  if (
    cols === 1 &&
    rows.length > 1 &&
    !isValidChemicalFormula(rows[0].target_compound_formula) &&
    isValidChemicalFormula(rows[1].target_compound_formula)
  ) {
    rows.shift()
  }
  return rows
}

/**
 * Validates compound rows parsed from a spreadsheet paste.
 *
 * Every row needs a formula. Single-column pastes are additionally checked
 * against isValidChemicalFormula, so that pasting a name-only column is
 * rejected instead of imported as bogus formulas.
 *
 * @param {Array<Object>} data - Rows from parseCompoundPaste
 * @returns {{valid: boolean, severity: string, message: string}}
 */
export function validateCompoundPaste(data) {
  if (!data || !Array.isArray(data) || data.length === 0 || !data[0]) {
    return { valid: false, severity: 'error', message: 'No valid data found in paste' }
  }
  const cols = Object.keys(data[0]).length
  if (cols > 3) {
    return {
      valid: false,
      severity: 'warn',
      message: `You pasted ${cols} columns but 1 to 3 are expected`
    }
  }
  if (data.some((row) => !row?.target_compound_formula?.length)) {
    return {
      valid: false,
      severity: 'warn',
      message: 'Some rows are missing a formula, which is required'
    }
  }
  if (cols === 1) {
    const invalid = data.find((row) => !isValidChemicalFormula(row.target_compound_formula))
    if (invalid) {
      return {
        valid: false,
        severity: 'warn',
        message: `'${invalid.target_compound_formula}' is not a valid chemical formula`
      }
    }
  }
  return {
    valid: true,
    severity: 'success',
    message: `Pasted ${data.length} compound${data.length === 1 ? '' : 's'}`
  }
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
