import { customAlphabet } from 'nanoid'

// ==== String manipulation functions ====

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

// ==== End string manipulation functions ====

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
