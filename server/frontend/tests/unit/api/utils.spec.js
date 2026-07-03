import { describe, it, expect } from 'vitest'

import { extractDistinctValues, generateCopyName, snakeToCamel } from '@/api/utils'

describe('extractDistinctValues', () => {
  it('deduplicates a property across objects', () => {
    const rows = [{ kind: 'a' }, { kind: 'b' }, { kind: 'a' }]
    expect(extractDistinctValues(rows, 'kind')).toEqual([{ kind: 'a' }, { kind: 'b' }])
  })

  it('returns an empty list for no input objects', () => {
    expect(extractDistinctValues([], 'kind')).toEqual([])
  })
})

describe('generateCopyName', () => {
  it.each([
    ['Report', 'Report Copy'],
    ['Report Copy', 'Report Copy(1)'],
    ['Report Copy(1)', 'Report Copy(2)'],
    ['Report Copy(9)', 'Report Copy(10)'],
    ['  Spaced   name ', 'Spaced name Copy']
  ])('turns %s into %s', (name, expected) => {
    expect(generateCopyName(name)).toBe(expected)
  })

  it('returns null for empty input', () => {
    expect(generateCopyName(null)).toBe(null)
    expect(generateCopyName('')).toBe(null)
  })
})

describe('snakeToCamel', () => {
  it('converts snake_case keys to camelCase', () => {
    expect(snakeToCamel('sample_item_id')).toBe('sampleItemId')
    expect(snakeToCamel('already')).toBe('already')
  })
})
