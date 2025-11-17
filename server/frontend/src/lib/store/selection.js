import { ref, computed, watch } from 'vue'
import { storeToRefs } from 'pinia'

import { api } from '@/api'
import { makeLogger } from '@/lib/logging'

import { useFilter } from '@/stores/data/filter'

export const useSelection = (name, key, records, options = {}) => {
  // CONFIG

  const { mode, subscribe, persist, hook } = {
    mode: 'binary', // | 'multiple' | 'single'
    subscribe: false,
    persist: false,
    hook: null,
    ...options
  }
  // logging
  const logger = makeLogger({
    prefix: `selection ${name}`,
    icon: '🌟'
  })

  // get filter from filter store
  const filterStore = useFilter()
  const filterRefs = storeToRefs(filterStore)
  let filter = filterRefs[name]

  // if no filter exists in filter store, create local reactive ref (guard)
  if (!filter) {
    logger.warn(`Creating local selection state for '${name}' (not in filter store)`)
    filter = ref([])
  }

  const singleselect = mode === 'single' || mode === 'binary'
  const multiselect = mode === 'multiple'
  const allowUnfocus = mode !== 'single'

  // selection state
  const selected = computed({
    get() {
      return filter.value ?? []
    },
    set(value) {
      filter.value = value ?? []
    }
  })
  const selectedIds = computed(() => selected.value.map((record) => record[key]))
  const isSelected = (arg) =>
    arg ? selected.value.map((record) => record[key]).includes(arg[key]) : false

  // focus state
  const focused = computed({
    get() {
      return filter.value.length === 1 ? filter.value[0] : null
    },
    set(value) {
      filter.value = value ? [value] : []
    }
  })
  const focusedId = computed(() => (focused.value ? focused.value[key] : null))
  const isFocused = (arg) => (arg && focused.value ? focused.value[key] === arg[key] : false)

  // methods
  const select = multiselect
    ? (...args) => {
        args.forEach((arg) => {
          if (!isSelected(arg)) {
            selected.value.push(records().find((record) => record[key] === arg[key]))
          }
        })
      }
    : // singleselect
      (arg) => {
        if (!isFocused(arg)) {
          focused.value = records().find((record) => record[key] === arg[key])
        }
      }
  const unselect = multiselect
    ? (...args) => {
        args.forEach((arg) => {
          if (isSelected(arg)) {
            selected.value = selected.value.filter((record) => record[key] !== arg[key])
          }
        })
      }
    : // singleselect
      (arg) => {
        if (isFocused(arg)) {
          focused.value = null
        }
      }
  const focus = multiselect
    ? (arg) => {
        if (!isFocused(arg)) {
          selected.value = [records().find((record) => record[key] === arg[key])].filter(
            (record) => !!record
          )
        }
      }
    : // singleselect
      (arg) => {
        if (typeof arg === 'function') {
          // allow predicates to focus with arbitrary conditions
          focused.value = records().find(arg)
        } else {
          // but normally, focus using a record or key field
          if (!isFocused(arg)) {
            focused.value = records().find((record) => record[key] === arg[key])
          }
        }
      }
  const unfocus = multiselect
    ? (arg) => {
        if (arg) {
          if (isSelected(arg)) {
            selected.value = []
          }
        } else {
          selected.value = []
        }
      }
    : // singleselect
      (arg) => {
        if (arg) {
          if (isFocused(arg)) {
            focused.value = null
          }
        } else {
          focused.value = null
        }
      }

  // lazy focusing
  const toFocus = ref(null)
  const lazyFocus = (arg) => {
    toFocus.value = arg
  }

  // focus logging
  if (singleselect) {
    watch(focused, (nextFocus, prevFocus) => {
      // Compare ids, not object references!
      const prevId = prevFocus ? prevFocus[key] : null
      const nextId = nextFocus ? nextFocus[key] : null
      if (prevId !== nextId) {
        if (prevFocus) {
          logger.debug(`unfocusing`, {
            icon: '☁️',
            data: { record: prevFocus }
          })
        }
        if (nextFocus) {
          logger.debug(`focusing`, {
            icon: '🔍',
            data: { record: nextFocus }
          })
        }
      }
    })
  }

  // selection logging
  if (multiselect) {
    watch(selected, (nextSelected, prevSelected) => {
      // Extract IDs for comparison
      const prevIds = prevSelected.map((p) => p[key])
      const nextIds = nextSelected.map((n) => n[key])

      let icon = '☁️'
      prevSelected.forEach((selected) => {
        const newlyUnselected = !nextIds.includes(selected[key])
        const data = { record: selected }
        if (newlyUnselected) {
          if (nextSelected.length >= 1) {
            logger.debug('unselecting', { icon, data })
          } else {
            logger.log('unfocusing', { icon, data })
          }
        }
      })
      icon = '🔍'
      nextSelected.forEach((selected) => {
        const newlySelected = !prevIds.includes(selected[key])
        const data = { record: selected }
        if (newlySelected) {
          if (!focused.value) {
            logger.debug('selecting', { icon, data })
          }
        }
      })
      if (focused.value) {
        const data = { record: focused.value }
        logger.debug('focusing', { icon, data })
      }
    })
  }

  // persistence

  const stateLoaded = ref(false)
  const storageKey = `module[${name}]`
  const restoreState = () => {
    if (!stateLoaded.value && persist) {
      const state = localStorage.getItem(storageKey)

      // Check for null, empty string, and 'undefined' string
      if (!state || state === 'undefined' || state === 'null') {
        logger.debug('state not found or invalid in storage', { data: { storageKey, state } })
        return false
      }

      // Verify the restored ID exists in current records
      const exists = records().some((record) => record[key] === state)
      if (!exists) {
        logger.debug('stored state no longer valid', { data: { storageKey, state } })
        localStorage.removeItem(storageKey) // Clean up invalid state
        return false
      }

      logger.debug('loading focus from storage', { data: { state, storageKey } })
      focus({ [key]: state })
      stateLoaded.value = true
      return true
    } else {
      return false
    }
  }
  const persistState = (record) => {
    if (record && record[key] != null) {
      logger.debug(`'saving focus to storage`, {
        icon: '💾',
        data: { record, storageKey }
      })
      localStorage.setItem(storageKey, record[key])
    } else {
      logger.warn(`'invalid record to save to storage`, {
        icon: '💾',
        data: { storageKey }
      })
    }
  }
  if (persist) {
    watch(focused, persistState)
  }

  // focus automation

  // automatically reassign next focus after reload
  const prepRefocus = () => () => {
    // Capture previous selection state BEFORE reload (works for both single & multi-select)
    const previousSelectedIds = selected.value.map((s) => s[key])

    // --- scheduled lazy focus takes priority ---
    const nextId = toFocus.value?.[key]
    const nextValid = records()
      .map((record) => record[key])
      .includes(nextId)
    if (nextId && nextValid) {
      logger.debug(`lazy refocusing on ${nextId}`)
      toFocus.value = null
      focus({ [key]: nextId })
      return focused.value
    }

    // --- Restore previous selection by IDs (both single/multi select) ---
    if (previousSelectedIds.length > 0) {
      const recordsToRestore = records().filter((r) => previousSelectedIds.includes(r[key]))
      if (recordsToRestore.length > 0) {
        logger.debug(`refocusing ${recordsToRestore.length} record(s)`)
        selected.value = recordsToRestore
        return focused.value
      }
    }
    // --- try to restore state from localStorage (only if persist enabled) ---
    const restored = restoreState()
    if (restored) {
      return focused.value
    }

    // --- try to unfocus if allowed ---
    if (allowUnfocus) {
      unfocus()
      return focused.value
    }

    // --- finally try to autofocus on the first record  as fallback ---
    const resolved = records().length > 0 ? records()[0] : null
    if (!resolved) {
      logger.warn('refocus failed to resolve the default record.')
      return focused.value // Return early when no record to focus
    }
    logger.debug(`autofocusing ${resolved[key]}`)
    focus(resolved)
    return focused.value
  }

  // EVENTS

  // manage socket room subscription
  if (subscribe) {
    let room = (record) => record[key]
    if (typeof subscribe === 'function') {
      room = subscribe
    }
    watch(focused, (next, prev) => {
      // Extract room IDs
      const prevRoom = prev ? room(prev) : null
      const nextRoom = next ? room(next) : null

      // Only unsubscribe/subscribe if room ID actually changed
      if (prevRoom !== nextRoom) {
        if (prevRoom) {
          logger.debug(`unsubscribing from`, {
            icon: '📪',
            data: { room: prevRoom }
          })
          api.socket.emit('unsubscribe', prevRoom)
        }
        if (nextRoom) {
          logger.debug(`subscribing to`, {
            icon: '📬',
            data: { room: nextRoom }
          })
          api.socket.emit('subscribe', nextRoom)
        }
      }
    })
  }

  // execute custom hook on refocus
  if (hook) {
    watch(focused, async (next, prev) => {
      hook({ next, prev }) // This is a custom callback,
    })
  }

  // API

  return {
    // options
    multiselect,
    singleselect,
    allowUnfocus,
    // selection
    selected,
    selectedIds,
    isSelected,
    select,
    unselect,
    // focus
    focused,
    focusedId,
    focus,
    unfocus,
    prepRefocus,
    lazyFocus
  }
}
