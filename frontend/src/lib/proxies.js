import { toRaw } from 'vue'

export function toRawDeep(observed) {
  console.log(observed)
  const val = toRaw(observed)

  if (Array.isArray(val)) {
    return val.map(toRawDeep)
  }

  if (val === null) return null

  if (typeof val === 'object') {
    const entries = Object.entries(val).map(([key, val]) => [key, toRawDeep(val)])

    return Object.fromEntries(entries)
  }

  return val
}
