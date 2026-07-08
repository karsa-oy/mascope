/**
 * URL <-> Location codec. A location is carried as query parameters so a link
 * is human-inspectable and works with the app's single history route. Only the
 * semantic chain and tab travel in the URL; personal presentation (splits,
 * theme) is deliberately left out.
 */
import { normalizeLocation, isEmptyLocation, LOCATION_VERSION } from './schema'

// Short query keys keep shared links compact.
const QUERY_KEYS = {
  v: 'v',
  workspace: 'w',
  dataset: 'd',
  batch: 'b',
  samples: 's',
  peak: 'p',
  collection: 'c',
  ions: 'i',
  visualizedIon: 'vi',
  isotope: 'iso',
  tab: 'tab'
}

const splitIds = (value) => (value ? value.split(',').filter(Boolean) : [])

/** True when a query carries any location parameter. */
export const hasLocationQuery = (params) => {
  const p = params instanceof URLSearchParams ? params : new URLSearchParams(params ?? '')
  return Object.values(QUERY_KEYS).some((key) => key !== QUERY_KEYS.v && p.has(key))
}

/** Serialize a Location into a URLSearchParams (empty when the location is). */
export const locationToQuery = (loc) => {
  const n = normalizeLocation(loc)
  const params = new URLSearchParams()
  if (isEmptyLocation(n)) return params

  const setId = (field, value) => value && params.set(QUERY_KEYS[field], value)
  const setIds = (field, ids) => ids.length && params.set(QUERY_KEYS[field], ids.join(','))

  setId('workspace', n.workspace)
  setId('dataset', n.dataset)
  setId('batch', n.batch)
  setIds('samples', n.samples)
  setId('peak', n.peak)
  setId('collection', n.collection)
  setIds('ions', n.ions)
  setId('visualizedIon', n.visualizedIon)
  setId('isotope', n.isotope)
  if (n.tab) params.set(QUERY_KEYS.tab, n.tab)
  params.set(QUERY_KEYS.v, String(LOCATION_VERSION))
  return params
}

/** Parse a query (string or URLSearchParams) back into a normalized Location. */
export const locationFromQuery = (params) => {
  const p = params instanceof URLSearchParams ? params : new URLSearchParams(params ?? '')
  return normalizeLocation({
    v: Number(p.get(QUERY_KEYS.v)) || undefined,
    workspace: p.get(QUERY_KEYS.workspace),
    dataset: p.get(QUERY_KEYS.dataset),
    batch: p.get(QUERY_KEYS.batch),
    samples: splitIds(p.get(QUERY_KEYS.samples)),
    peak: p.get(QUERY_KEYS.peak),
    collection: p.get(QUERY_KEYS.collection),
    ions: splitIds(p.get(QUERY_KEYS.ions)),
    visualizedIon: p.get(QUERY_KEYS.visualizedIon),
    isotope: p.get(QUERY_KEYS.isotope),
    tab: p.get(QUERY_KEYS.tab)
  })
}

/** Build a full shareable URL for a location against a base origin+path. */
export const locationToUrl = (loc, { origin, pathname } = {}) => {
  const base = `${origin ?? ''}${pathname ?? '/'}`
  const query = locationToQuery(loc).toString()
  return query ? `${base}?${query}` : base
}
