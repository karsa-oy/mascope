import { ref, shallowRef, computed, watch, onMounted } from 'vue'

import { api } from '@/api'
import { useAuth } from '@/stores/auth'
import { genId } from '@/lib/utils'
import { makeLogger } from '@/lib/logging'

import { useSelection } from './selection'

export const useData = (
  // required
  name,
  method,
  // optional
  options = {}
) => {
  // CONFIG

  // destructure options and set defaults
  const { key, events, deps, hook } = {
    deps: null,
    events: [],
    hook: () => {}, // runs on event only for now; TODO: make universal
    key: `${name}_id`,
    ...options
  }

  // Optional extensions accessed from options
  const { read, detailed } = options
  // read - function to read single record by id
  // detailed - ref to hold detailed record data with associations

  // logging
  const logger = makeLogger({
    prefix: `data ${name}`,
    icon: '🗃️'
  })

  // utils
  const noop = () => {}

  // DATA

  // raw data
  const records = shallowRef([]) // private
  // read-only data
  const list = computed(() => {
    // aggregation / joins
    return records.value
  })

  // conditionally initialize selection
  const selection = options?.selection
    ? useSelection(
        name,
        key,
        () => records.value,
        options.selection === true
          ? {} // use defaults if set to true
          : options.selection // pass options otherwise
      )
    : null

  // filtering
  const filtered = computed(() =>
    selection?.selected && selection.selected.value.length > 0
      ? selection.selected.value
      : list.value
  )
  const filteredIds = computed(() => filtered.value.map((record) => record[key]))

  // state
  const pending = ref(false)

  // hook
  /**
   * Synchronizes store data by fetching from API and updating reactive state.
   * Populates the store's .list with records and manages focus/selection state.
   *
   * @param {Object} trigger - Information about what triggered this sync (context, event)
   */
  const sync = async (trigger) => {
    // previous state setup
    const refocus = selection?.prepRefocus() ?? noop
    const oldCount = records.value.length
    const context = trigger?.context ?? 'unknown'

    logger.debug(`sync triggered by ${trigger?.event ? `${context} (${trigger.event})` : context}`)
    pending.value = true

    // Dependencies resolution
    const args = deps ? deps() : undefined

    // log all dependencies on initialization
    if (deps && args && context === 'initialization') {
      const allDeps = Object.keys(args)
        .map((key) => key.replace(/_(id|ids|filter)s?$/, '')) // Remove suffixes
        .join(', ')
      logger.debug(`dependencies: ${allDeps}`)
    }

    const unmetDeps = args
      ? Object.entries(args)
          .filter(([key, value]) => value === null)
          .map(([key]) => key.replace(/_(id|ids|filter)s?$/, ''))
      : []

    const hasUnmetDeps = unmetDeps.length > 0

    // data loading
    if (hasUnmetDeps) {
      records.value = []
      logger.debug(`waiting for ${unmetDeps.join(', ')} dependency change for loading`)
    } else {
      // Load data from API
      records.value = (await method(args)) || []
      // Add index field to all records
      records.value.forEach((record, index) => (record.index = (index + 1).toString()))
    }

    // Status Logging
    const newCount = records.value.length
    if (newCount === 0) {
      if (oldCount > 0) {
        logger.log('cleared') // Had data, now empty
      } else if (!hasUnmetDeps) {
        // case for no records
        logger.log(`${context === 'socket event' ? 'reloaded' : 'loaded'} (0 records)`)
      }
    } else {
      // Has records
      const status = (() => {
        switch (context) {
          case 'initialization':
          case 'dependencies':
            return 'loaded'
          case 'socket event':
            return 'reloaded'
          default:
            return oldCount === 0 ? 'loaded' : 'reloaded'
        }
      })()

      logger.log(`${status} (${newCount} records)`)
    }
    // state management
    refocus()
    pending.value = false
  }

  const reloadRecord = async () => {
    if (!selection?.focused?.value || !read) return

    // Capture the ID before async operation to prevent race conditions
    const recordId = selection.focused.value[key]

    try {
      logger.debug(`reload focused record ${recordId}`)
      const freshRecord = await read(recordId)

      // Guard: Check if selection still focused on same record after async operation
      if (!selection?.focused?.value || selection.focused.value[key] !== recordId) {
        logger.debug(`record ${recordId} unfocused during reload - skipping update`)
        return
      }

      // Guard: Check if read returned valid data
      if (!freshRecord) {
        logger.warn(`reload focused record ${recordId} returned null/undefined`)
        return
      }

      // Update the record in the list
      const index = records.value.findIndex((r) => r[key] === recordId)
      if (index >= 0) {
        records.value[index] = freshRecord
      }

      // Update focused reference if in singleselect mode
      if (selection.singleselect) {
        selection.focused.value = freshRecord
      }

      // Update detailed data if provided
      if (detailed) {
        detailed.value = freshRecord
      }

      return freshRecord
    } catch (error) {
      logger.warn(`failed to reload focused record ${selection?.focused.value[key]}: ${error}`)
      return
    }
  }

  const load = (context) => sync({ context })

  // load on init, all root stores initialize themselves
  onMounted(() => {
    const auth = useAuth()
    auth.onLogin(() => {
      sync({ context: 'initialization' })
    })
  })

  // reload when dependencies change
  if (deps) {
    watch(deps, (next, prev) => {
      if (JSON.stringify(next) !== JSON.stringify(prev)) {
        // Find and log changes
        Object.keys({ ...prev, ...next })
          .filter((key) => JSON.stringify(next?.[key]) !== JSON.stringify(prev?.[key]))
          .forEach((key) => {
            logger.debug(`dependency change for ${key}: ${prev?.[key]} -> ${next?.[key]}`, {
              icon: '🔄',
              data: { key, from: prev?.[key], to: next?.[key] }
            })
          })

        sync({ context: 'dependencies' })
      }
    })
  }

  // reload events

  events.forEach((event) => {
    api.socket.on(event, async () => {
      await sync({ context: 'socket event', event: event })
      await reloadRecord()
      hook()
    })
  })

  // API

  return {
    list,
    pending,
    load,
    filtered,
    filteredIds,
    // Only expose if provided
    ...(detailed && { detailed }),
    ...(selection ?? {})
  }
}
