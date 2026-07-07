import { watch } from 'vue'
import { defineStore } from 'pinia'

import { makeLogger } from '@/lib/logging'
import { useApp } from '@/stores'

import { LOCATION_LEVELS, normalizeLocation, levelIds } from './schema'

export * from './schema'

const logger = makeLogger({ prefix: 'location', icon: '🧭' })

// How long to wait for a restored chain to converge before giving up on the
// deferred visualization restore.
const CONVERGE_TIMEOUT_MS = 30000

// Resolve a dotted store path (e.g. 'match.collection') against app.data.
const resolveStore = (data, path) => path.split('.').reduce((node, part) => node?.[part], data)

/**
 * Drive a single chain level toward its target ids. Levels whose target
 * records are already resident are applied immediately; otherwise the target is
 * queued (lazyFocus / lazySelect) so it applies as the data streams in behind
 * the parent's focus.
 */
const applyLevel = (store, level, loc) => {
  const ids = levelIds(loc, level)
  const { key, multi } = level

  if (ids.length === 0) {
    store.unfocus?.()
    return
  }

  const present = store.list.filter((record) => ids.includes(record[key]))
  const allPresent = present.length === ids.length

  if (multi) {
    if (allPresent) {
      store.unfocus?.()
      store.select?.(...ids.map((id) => ({ [key]: id })))
    } else {
      store.lazySelect?.(ids)
    }
  } else if (allPresent) {
    store.focus?.({ [key]: ids[0] })
  } else {
    store.lazyFocus?.({ [key]: ids[0] })
  }
}

/**
 * The match visualization is imperative state, not a data store, so it is
 * restored last: once the sample, collection and ion it needs have focused,
 * fire a single set(). Only a single-sample context is restorable (the
 * visualization query is per focused sample).
 */
const restoreVisualization = (data, loc) => {
  if (!loc.collection || loc.ions.length === 0 || loc.samples.length !== 1) return

  const sampleId = loc.samples[0]
  const collectionId = loc.collection
  const ionId = loc.ions[0]
  const isotopeId = loc.isotope

  const ready = () =>
    data.sample.focusedId === sampleId &&
    data.match.collection.focusedId === collectionId &&
    data.match.ion.selectedIds.includes(ionId)

  const restore = () => {
    logger.debug('restoring visualization', { data: { sampleId, collectionId, ionId } })
    data.match.visualized.set({ sampleId, collectionId, ionId, isotopeId })
  }

  // Already resident and focused (in-session apply): restore now.
  if (ready()) {
    restore()
    return
  }

  // Otherwise wait for the chain to converge, then fire once.
  const stop = watch(ready, (isReady) => {
    if (!isReady) return
    restore()
    stop()
  })

  // Give up watching if the context never resolves (e.g. no access to the ion).
  setTimeout(stop, CONVERGE_TIMEOUT_MS)
}

export const useLocation = defineStore('app.location', () => {
  /**
   * Derive the current Location from the live stores.
   */
  const read = () => {
    const { data, ui } = useApp()
    const raw = {}
    for (const level of LOCATION_LEVELS) {
      const store = resolveStore(data, level.path)
      if (!store) continue
      raw[level.field] = level.multi ? [...store.selectedIds] : store.focusedId
    }
    raw.isotope = data.match.visualized.isotopeSelected?.target_isotope_id ?? null
    raw.tab = ui.tab.active
    return normalizeLocation(raw)
  }

  /**
   * Drive the stores to converge on a target location: the chain, then the
   * visualization, then the active tab.
   */
  const apply = (input) => {
    const loc = normalizeLocation(input)
    const { data, ui } = useApp()
    logger.debug('applying location', { data: { loc } })

    for (const level of LOCATION_LEVELS) {
      const store = resolveStore(data, level.path)
      if (store) applyLevel(store, level, loc)
    }

    restoreVisualization(data, loc)
    // 'match' is reached through the visualization above; the tab store's own
    // guards keep it there. Other tabs are hydrated directly.
    if (loc.tab && loc.tab !== 'match') ui.tab.hydrate(loc.tab)
  }

  return { read, apply }
})
