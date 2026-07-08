import { describe, it, expect } from 'vitest'
import {
  locationToQuery,
  locationFromQuery,
  locationToUrl,
  hasLocationQuery
} from '@/lib/location/url'
import { LOCATION_VERSION } from '@/lib/location/schema'

describe('location URL codec', () => {
  it('round-trips a full location through the query string', () => {
    const loc = {
      workspace: 'w1',
      dataset: 'd1',
      batch: 'b1',
      samples: ['s1', 's2'],
      peak: 'p1',
      collection: 'c1',
      ions: ['i1', 'i2'],
      visualizedIon: 'i2',
      isotope: 'iso1',
      tab: 'match'
    }

    const query = locationToQuery(loc).toString()
    const back = locationFromQuery(query)

    expect(back).toMatchObject(loc)
    expect(back.v).toBe(LOCATION_VERSION)
  })

  it('uses compact keys and stamps the version', () => {
    const params = locationToQuery({ workspace: 'w1', samples: ['s1', 's2'] })
    expect(params.get('w')).toBe('w1')
    expect(params.get('s')).toBe('s1,s2')
    expect(params.get('v')).toBe(String(LOCATION_VERSION))
  })

  it('produces an empty query for an empty location', () => {
    expect(locationToQuery({}).toString()).toBe('')
    expect(locationToUrl({}, { origin: 'https://x', pathname: '/' })).toBe('https://x/')
  })

  it('builds a full shareable URL', () => {
    const url = locationToUrl(
      { batch: 'b1', tab: 'batch' },
      { origin: 'https://mascope.example', pathname: '/' }
    )
    expect(url).toMatch(/^https:\/\/mascope\.example\/\?/)
    expect(url).toContain('b=b1')
    expect(url).toContain('tab=batch')
  })

  it('detects whether a query carries a location', () => {
    expect(hasLocationQuery('w=w1')).toBe(true)
    expect(hasLocationQuery('?b=b1&v=1')).toBe(true)
    expect(hasLocationQuery('v=1')).toBe(false) // version alone is not a location
    expect(hasLocationQuery('')).toBe(false)
    expect(hasLocationQuery('foo=bar')).toBe(false)
  })

  it('preserves a tab value that contains a space', () => {
    const query = locationToQuery({ workspace: 'w1', tab: 'raw files' }).toString()
    expect(locationFromQuery(query).tab).toBe('raw files')
  })

  it('drops malformed / unknown query params via normalization', () => {
    const loc = locationFromQuery('w=w1&s=,,s2,&tab=bogus')
    expect(loc.workspace).toBe('w1')
    expect(loc.samples).toEqual(['s2']) // empty segments filtered
    expect(loc.tab).toBe(null) // invalid tab rejected
  })
})
