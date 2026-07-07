import { computed, watch } from 'vue'
import { defineStore } from 'pinia'

import { makeLogger } from '@/lib/logging'
import { debounce } from '@/lib/utils'
import { useApp } from '@/stores'
import { useAuth } from '@/stores/auth'

import { LOCATION_LEVELS, normalizeLocation, levelIds } from './schema'
import { hasLocationQuery, locationFromQuery, locationToUrl } from './url'

export * from './schema'
export * from './url'

const logger = makeLogger({ prefix: 'location', icon: '🧭' })

// How long to wait for a restored chain to converge before giving up on the
// deferred visualization restore.
const CONVERGE_TIMEOUT_MS = 30000

// How long to let a shared location converge before checking which levels
// actually resolved, so we can warn about anything the viewer cannot access.
const VERIFY_DELAY_MS = 4000

// Debounce for mirroring the location into the address bar; collapses the burst
// of intermediate changes while a chain converges into a single URL write.
const MIRROR_DEBOUNCE_MS = 400

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

  /**
   * After a shared location has had time to converge, warn about any requested
   * level that did not resolve - typically because the viewer lacks access to
   * that workspace/dataset or the record was deleted.
   */
  const verifyApplied = (requested) => {
    setTimeout(() => {
      const current = read()
      const missing = LOCATION_LEVELS.filter((level) => {
        const want = levelIds(requested, level)
        if (want.length === 0) return false
        const have = levelIds(current, level)
        return want.some((id) => !have.includes(id))
      }).map((level) => level.field)

      if (missing.length > 0) {
        logger.warn('shared location partially unresolved', { data: { missing } })
        useApp().ui.notification.push({
          type: 'shared_link',
          status: 'warning',
          message: `Part of the shared view could not be opened (${missing.join(', ')}); you may not have access to it.`
        })
      }
    }, VERIFY_DELAY_MS)
  }

  /** Full shareable URL for the current location. */
  const shareUrl = () =>
    locationToUrl(read(), {
      origin: window.location.origin,
      pathname: window.location.pathname
    })

  /** Copy a link to the current view to the clipboard, notifying the user. */
  const copyShareLink = async () => {
    const url = shareUrl()
    const { ui } = useApp()
    try {
      await navigator.clipboard.writeText(url)
      ui.notification.push({
        type: 'shared_link',
        status: 'success',
        message: 'Link to this view copied to clipboard'
      })
    } catch (error) {
      logger.warn('clipboard write failed', { data: { error: String(error) } })
      ui.notification.push({
        type: 'shared_link',
        status: 'warning',
        message: 'Could not copy the link automatically'
      })
    }
    return url
  }

  /**
   * If the current URL carries a shared location, apply it (winning over the
   * personal snapshot) and schedule an access check. When mirroring is off the
   * query is stripped so a later manual reload falls through to the personal
   * snapshot; when mirroring is on the mirror keeps the address bar in sync, so
   * the query is left for it to manage.
   */
  const importFromUrl = () => {
    const search = window.location.search
    if (!hasLocationQuery(search)) return false

    const loc = locationFromQuery(search)
    logger.log('opening shared location from URL')
    apply(loc)
    if (!mirroring) window.history.replaceState({}, '', window.location.pathname)
    verifyApplied(loc)
    return true
  }

  // --- URL mirroring ---
  // Continuously reflect the current location into the address bar so it is
  // always bookmarkable/shareable, using replaceState (not pushState) so we do
  // not flood browser history.
  let mirroring = false

  const writeUrl = (loc) => {
    const url = locationToUrl(loc, {
      origin: window.location.origin,
      pathname: window.location.pathname
    })
    const target = url.slice(window.location.origin.length)
    if (target !== window.location.pathname + window.location.search) {
      window.history.replaceState({}, '', url)
    }
  }

  const enableMirroring = () => {
    if (mirroring) return
    mirroring = true
    const current = computed(read)
    const mirror = debounce((loc) => writeUrl(loc), MIRROR_DEBOUNCE_MS)
    watch(current, (loc) => mirror(loc))
  }

  // Import a shared location once the user is authenticated and the stores
  // start loading; the lazy targets set by apply() win the ensuing refocus.
  useAuth().onLogin(() => importFromUrl())

  return { read, apply, shareUrl, copyShareLink, importFromUrl, enableMirroring }
})
