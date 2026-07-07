import { describe, it, expect } from 'vitest'

import { fromSpreadsheet, equals } from '@/lib/table'

const TAB = String.fromCharCode(9)
const NL = String.fromCharCode(10)

describe('fromSpreadsheet', () => {
  it('infers fields from the header row', () => {
    const text = ['Compound Name' + TAB + 'Formula', 'benzene' + TAB + 'C6H6'].join(NL)

    const { cols, rows } = fromSpreadsheet(text)

    expect(cols).toEqual([
      { field: 'compound_name', label: 'Compound Name' },
      { field: 'formula', label: 'Formula' }
    ])
    expect(rows).toEqual([{ compound_name: 'benzene', formula: 'C6H6' }])
  })

  it('uses provided fields and treats every line as a body row', () => {
    const text = ['benzene' + TAB + 'C6H6', 'toluene' + TAB + 'C7H8'].join(NL)

    const { cols, rows } = fromSpreadsheet(text, ['name', 'formula'])

    expect(cols.map((c) => c.field)).toEqual(['name', 'formula'])
    expect(rows).toEqual([
      { name: 'benzene', formula: 'C6H6' },
      { name: 'toluene', formula: 'C7H8' }
    ])
  })

  it('trims cell whitespace and skips empty lines', () => {
    const text = 'name' + NL + ' benzene ' + NL + NL

    const { rows } = fromSpreadsheet(text)

    expect(rows).toEqual([{ name: 'benzene' }])
  })

  it('survives Windows clipboard content (CRLF)', () => {
    // Excel on Windows pastes CRLF line endings; the trailing \r must not
    // leak into field values.
    const text = 'name\r' + NL + 'benzene\r'

    const { rows } = fromSpreadsheet(text)

    expect(rows).toEqual([{ name: 'benzene' }])
  })
})

describe('equals', () => {
  it('compares arrays by field, ignoring order', () => {
    const a = [{ id: '1' }, { id: '2' }]
    const b = [{ id: '2' }, { id: '1' }]

    expect(equals(a, b, 'id')).toBe(true)
    expect(equals(a, [{ id: '1' }], 'id')).toBe(false)
  })

  it('compares single records by field', () => {
    expect(equals({ id: '1' }, { id: '1' }, 'id')).toBe(true)
    expect(equals({ id: '1' }, { id: '2' }, 'id')).toBe(false)
  })

  it('treats two nullish inputs as equal and nullish-vs-record as unequal', () => {
    expect(equals(null, undefined, 'id')).toBe(true)
    expect(equals(null, { id: '1' }, 'id')).toBe(false)
    expect(equals({ id: '1' }, null, 'id')).toBe(false)
  })
})
