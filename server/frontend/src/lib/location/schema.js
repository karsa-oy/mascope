/**
 * Canonical description of "where the app is": the chain of focused/selected
 * record ids plus the active tab. This is the single source of truth for the
 * navigation shape, shared by every reader and writer (localStorage snapshot,
 * URL codec, store applier). It is deliberately free of Vue/Pinia so it can be
 * unit tested and reused anywhere.
 */

export const LOCATION_VERSION = 1

/**
 * The ordered navigation chain. Each level maps a location field to the store
 * that owns it (dotted path resolved against `app.data`), the record key used
 * to identify a selection, and whether the level is multi-select.
 */
export const LOCATION_LEVELS = [
  { field: 'workspace', path: 'workspace', key: 'workspace_id', multi: false },
  { field: 'dataset', path: 'dataset', key: 'dataset_id', multi: false },
  { field: 'batch', path: 'batch', key: 'sample_batch_id', multi: false },
  { field: 'samples', path: 'sample', key: 'sample_item_id', multi: true },
  { field: 'peak', path: 'peak', key: 'peak_id', multi: false },
  { field: 'collection', path: 'match.collection', key: 'target_collection_id', multi: false },
  { field: 'ions', path: 'match.ion', key: 'target_ion_id', multi: true }
]

export const VALID_TABS = ['raw files', 'batch', 'sample', 'match']

export const emptyLocation = () => ({
  v: LOCATION_VERSION,
  workspace: null,
  dataset: null,
  batch: null,
  samples: [],
  peak: null,
  collection: null,
  ions: [],
  // The ion whose match visualization is open, if any. Distinct from `ions`
  // (the multi-select table selection): selecting ions does not open the
  // visualization, so only this drives the visualization restore.
  visualizedIon: null,
  isotope: null,
  tab: null
})

const asId = (value) => (typeof value === 'string' && value ? value : null)
const asIds = (value) =>
  Array.isArray(value) ? value.filter((v) => typeof v === 'string' && v) : []

/**
 * Coerce an arbitrary parsed object (from storage or a URL) into a valid
 * Location, dropping unknown keys and normalizing types. Always stamps the
 * current version; callers decide how to treat a version mismatch on the raw
 * input before normalizing.
 */
export const normalizeLocation = (raw) => {
  if (!raw || typeof raw !== 'object') return emptyLocation()
  return {
    v: LOCATION_VERSION,
    workspace: asId(raw.workspace),
    dataset: asId(raw.dataset),
    batch: asId(raw.batch),
    samples: asIds(raw.samples),
    peak: asId(raw.peak),
    collection: asId(raw.collection),
    ions: asIds(raw.ions),
    visualizedIon: asId(raw.visualizedIon),
    isotope: asId(raw.isotope),
    tab: VALID_TABS.includes(raw.tab) ? raw.tab : null
  }
}

/** True when a location carries no navigational information. */
export const isEmptyLocation = (loc) => {
  const n = normalizeLocation(loc)
  return (
    !n.workspace &&
    !n.dataset &&
    !n.batch &&
    n.samples.length === 0 &&
    !n.peak &&
    !n.collection &&
    n.ions.length === 0 &&
    !n.visualizedIon &&
    !n.isotope &&
    !n.tab
  )
}

/** Value-equality of two locations, ignoring key order and version noise. */
export const locationsEqual = (a, b) =>
  JSON.stringify(normalizeLocation(a)) === JSON.stringify(normalizeLocation(b))

/** Ids for a chain level, always as an array (0/1 for single-select levels). */
export const levelIds = (loc, level) => {
  const value = loc?.[level.field]
  if (level.multi) return asIds(value)
  const id = asId(value)
  return id ? [id] : []
}
