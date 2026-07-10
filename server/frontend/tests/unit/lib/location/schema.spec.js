import { describe, it, expect } from 'vitest'
import {
  LOCATION_VERSION,
  emptyLocation,
  normalizeLocation,
  isEmptyLocation,
  locationsEqual,
  levelIds,
  LOCATION_LEVELS
} from '@/lib/location/schema'

const level = (field) => LOCATION_LEVELS.find((l) => l.field === field)

describe('location schema', () => {
  it('stamps the current version on an empty location', () => {
    expect(emptyLocation().v).toBe(LOCATION_VERSION)
    expect(isEmptyLocation(emptyLocation())).toBe(true)
  })

  it('normalizes ids and drops unknown / mistyped fields', () => {
    const loc = normalizeLocation({
      v: 999,
      workspace: 'w1',
      dataset: '',
      batch: 42,
      samples: ['s1', 's2', 7, null],
      ions: 'not-an-array',
      bogus: 'nope',
      tab: 'match'
    })

    expect(loc.v).toBe(LOCATION_VERSION) // version always restamped
    expect(loc.workspace).toBe('w1')
    expect(loc.dataset).toBe(null) // empty string -> null
    expect(loc.batch).toBe(null) // non-string -> null
    expect(loc.samples).toEqual(['s1', 's2']) // non-strings filtered out
    expect(loc.ions).toEqual([]) // non-array -> []
    expect(loc.tab).toBe('match')
    expect(loc).not.toHaveProperty('bogus')
  })

  it('rejects an invalid tab value', () => {
    expect(normalizeLocation({ tab: 'nonsense' }).tab).toBe(null)
    expect(normalizeLocation({ tab: 'sample' }).tab).toBe('sample')
  })

  it('treats a chain-only location as non-empty', () => {
    expect(isEmptyLocation({ workspace: 'w1' })).toBe(false)
    expect(isEmptyLocation({ ions: ['i1'] })).toBe(false)
    expect(isEmptyLocation({ tab: 'batch' })).toBe(false)
    expect(isEmptyLocation({ samples: [] })).toBe(true)
  })

  it('compares locations by value, ignoring key order and version', () => {
    expect(locationsEqual({ workspace: 'w1', v: 1 }, { v: 999, workspace: 'w1' })).toBe(true)
    expect(locationsEqual({ workspace: 'w1' }, { workspace: 'w2' })).toBe(false)
  })

  it('returns level ids as an array for single- and multi-select levels', () => {
    const loc = normalizeLocation({ batch: 'b1', samples: ['s1', 's2'] })
    expect(levelIds(loc, level('batch'))).toEqual(['b1'])
    expect(levelIds(loc, level('samples'))).toEqual(['s1', 's2'])
    expect(levelIds(loc, level('peak'))).toEqual([])
  })
})
