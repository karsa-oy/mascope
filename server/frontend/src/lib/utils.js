import { customAlphabet } from 'nanoid'

// STRINGS

export function beautifySnakeCase(str) {
  // Replace underscores with white space and capitalize first letter
  return capitalizeFirstLetter(str.replaceAll('_', ' '))
}

export function strToSnakeCase(str) {
  // Convert any string to snake_case
  return str
    .replace(/\W+/g, ' ')
    .split(/ |\B(?=[A-Z])/)
    .map((word) => word.toLowerCase())
    .join('_')
}

export function capitalizeFirstLetter(str) {
  // Capitalize first letter of a string
  return str[0].toUpperCase() + str.slice(1)
}

/**
 * Beautify an upper case SNAKE_CASE string by converting it to a capitalized, readable label.
 * e.g., 'FILTER_REGENERATION' -> 'Filter Regeneration'
 */
export function beautifyConstant(str) {
  return str
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

// MISC

export function genId(len, case_sensitive = true) {
  let alphabet
  if (case_sensitive) {
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
  } else {
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  }
  const nanoid = customAlphabet(alphabet, len)
  return nanoid()
}

export function clone(object) {
  return object ? JSON.parse(JSON.stringify(object)) : object
}

export function debounce(callback, timeout = 500) {
  let timeoutId = null
  return (...args) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => {
      callback(...args)
    }, timeout)
  }
}

export function instrumentType(instrument) {
  if (!instrument) {
    return null
  }
  const name = instrument.toLowerCase()
  if (name.includes('orbi')) {
    return 'orbi'
  } else if (name.includes('tof') || name.includes('api')) {
    return 'tof'
  } else {
    return null
  }
}
