import { ref, computed, watch, onMounted } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'
import { useAuth } from '@/stores/auth'

export const defineModule = ({
  name, // module name (snake_case)
  key, // data key (normally id)
  useParent = null, // optionally define a parent module
  subscribe = false, // make socket io subscription for key
  reloadOn = null, // events to reload the module on
  unfocusBefore = [], // unfucus before running these ops
  multiselect = false, // currently not in use
  allowUnfocus = true, // whether to allow unfocusing
  persist = false, // whether to save focus to local storage
  onRefocus = () => {}, // lifecycle hook executed after refocus
  onEvent = () => {}, // lifecycle hook executed after event reload
  // api
  load, // async func, may accept parent record
  read, // get one record by id
  ...ops // other operations optional
}) =>
  defineStore(`app.data.${name.replaceAll('_', '.')}`, () => {
    // CONFIG

    const prefix = `[app.data.${name.replaceAll('_', ' ')}]`
    const log = (message, ...rest) => console.log(`🔄 ${prefix} ${message}`, ...rest)
    const warn = (message, ...rest) => console.warn(`🔄 ${prefix} ${message}`, ...rest)
    const debug = (message, ...rest) => console.debug(`🔄 ${prefix} ${message}`, ...rest)

    const singleselect = !multiselect
    const parent = useParent ? useParent() : null

    // DATA

    // raw data
    const records = ref([])
    // read-only data
    const list = computed(() => {
      // aggregation / joins
      return records.value
    })

    // SELECTION

    // a dual API is exposed, which augments its behavior
    // based on the module's configuration:

    //  API       |  Type          |  Singleselect mode      |  Multiselect mode
    //  ---------------------------------------------------------------------------
    //  selected  |  record array  |  Computed (read-only)   |  Bindable (read/write)
    //  focused   |  record / null |  Bindable (read/write)  |  Computed (read-only)

    // This allows you to count on both APIs being available for read scenarios
    // but ensures you don't accidently corrupt state through inconsistent binds.

    // state
    const selected = multiselect ? ref([]) : computed(() => (focused.value ? [focused.value] : []))
    const focused = singleselect
      ? ref(null)
      : computed(() => (selected.value?.length === 1 ? selected.value[0] : null))
    const focusedId = computed(() => (focused.value ? focused.value[key] : null))
    const selectedIds = computed(() => selected.value.map((record) => record[key]))
    const isSelected = (arg) =>
      arg ? selected.value.map((record) => record[key]).includes(arg[key]) : false
    const isFocused = (arg) => (arg && focused.value ? focused.value[key] === arg[key] : false)

    // methods
    const select = multiselect
      ? (...args) => {
          args.forEach((arg) => {
            if (!isSelected(arg)) {
              selected.value.push(records.value.find((record) => record[key] === arg[key]))
            }
          })
        }
      : // singleselect
        (arg) => {
          if (!isFocused(arg)) {
            focused.value = records.value.find((record) => record[key] === arg[key])
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
          if (!isSelected(arg)) {
            selected.value = [records.value.find((record) => record[key] === arg[key])]
          }
        }
      : // singleselect
        (arg) => {
          if (typeof arg === 'function') {
            // allow predicates to focus with arbitrary conditions
            focused.value = records.value.find(arg)
          } else {
            // but normally, focus using a record or key field
            if (!isFocused(arg)) {
              focused.value = records.value.find((record) => record[key] === arg[key])
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

    // focus logging
    if (singleselect) {
      watch(focused, (nextFocus, prevFocus) => {
        if (nextFocus !== prevFocus) {
          if (prevFocus) {
            console.debug(`☁️ ${prefix} unfocusing`, prevFocus)
          }
          if (nextFocus) {
            console.debug(`⭐ ${prefix} focusing`, nextFocus)
          }
        }
      })
    }

    // selection logging
    if (multiselect) {
      watch(selected, (nextSelected, prevSelected) => {
        prevSelected.forEach((selected) => {
          const newlyUnselected = !nextSelected.map((p) => p[key]).includes(selected[key])
          if (newlyUnselected) {
            if (nextSelected.length >= 1) {
              console.debug(`☁️ ${prefix} unselecting`, selected)
            } else {
              console.log(`☁️ ${prefix} unfocusing`, selected)
            }
          }
        })
        nextSelected.forEach((selected) => {
          const newlySelected = !prevSelected.map((p) => p[key]).includes(selected[key])
          if (newlySelected) {
            if (!focused.value) {
              console.debug(`✨ ${prefix} selecting`, selected)
            }
          }
        })
        if (focused.value) {
          console.log(`⭐ ${prefix} focusing`, focused.value)
        }
      })
    }

    // persistence

    const stateLoaded = ref(false)
    const storageKey = `module[${name}]`
    const restoreState = () => {
      if (!stateLoaded.value && persist) {
        const state = localStorage.getItem(storageKey)
        if (!state) {
          debug('state not found storage')
          return false
        }
        debug('loading focus from storage', state)
        focus({ [key]: state })
        stateLoaded.value = true
        return true
      } else {
        return false
      }
    }
    const persistState = (record) => {
      if (record) {
        debug('saving focus to storage', record[key])
        localStorage.setItem(storageKey, record[key])
      }
    }
    if (persist) {
      watch(focused, persistState)
    }

    // focus automation

    // automatically reassign next focus after reload
    const refocus = (previousId) => {
      // using the previously focused value
      const previousValid = records.value.map((record) => record[key]).includes(previousId)
      if (previousId && previousValid) {
        debug(`refocusing on ${previousId}`)
        focus({ [key]: previousId })
        return focused.value
      }
      // then try to restore state
      const restored = restoreState()
      if (restored) {
        return focused.value
      }
      // then try to unfocus if allowed
      if (allowUnfocus) {
        unfocus()
        return focused.value
      }
      // finally try to autofocus on the first record
      const resolved = records.value.length > 0 ? records.value[0] : null
      if (!resolved) {
        warn('refocus failed to resolve the default record.')
      }
      debug(`autofocusing ${resolved[key]}`)
      focus(resolved)
      return focused.value
    }

    // LOADING

    // state
    const loading = ref(false)

    // children
    const children = ref([])
    const register = (child) => {
      children.value.push(child)
    }

    // hook
    const reload = async (trigger) => {
      const oldFocusedId = focused.value ? focused.value[key] : null
      debug(`load triggered by ${trigger?.event ?? trigger?.name ?? 'unknown'}`)
      loading.value = true
      if (trigger?.name) {
        records.value = trigger?.focused ? await load(trigger.focused) : []
      } else {
        records.value = await load()
      }
      records.value.forEach((record, index) => (record.index = (index + 1).toString()))
      log('data loaded')
      const newFocused = refocus(oldFocusedId)
      // propegate to children
      if (children.value.length > 0) {
        await Promise.all(children.value.map(({ reload }) => reload({ name, focused: newFocused })))
        debug('child data loaded')
      }
      loading.value = false
    }

    // load on init
    onMounted(() => {
      const auth = useAuth()
      auth.onLogin(() => {
        if (!parent) {
          // root modules self init on mount
          reload({ event: 'initialization' })
        }
      })
    })

    if (parent) {
      // child modules init with parent
      parent.register({ reload })
    }

    // reload children on refocus
    watch(focused, async (focused) => {
      await Promise.all(
        children.value.map(({ reload }) =>
          reload({
            name,
            focused
          })
        )
      )
      onRefocus()
    })

    // unfocus before calling certain methods
    const wrappedOps = Object.fromEntries(
      Object.entries(ops).map(([name, func]) =>
        unfocusBefore.includes(name)
          ? [
              name,
              (...args) => {
                unfocus()
                return func(...args)
              }
            ]
          : [name, func]
      )
    )

    // event triggered reloading

    if (!parent) {
      api.socket.on(`org_reload`, () => reload({ event: 'org_reload' }))
    }

    // Hook the module to reload its data under specific conditions
    const reloadHandler =
      // Check if the parent is a virtual parent (used for special cases like match data)
      parent && parent.name.includes('virtual')
        ? reload // For virtual parents, reload without passing trigger arguments
        : () =>
            reload({
              name: parent?.name,
              focused: parent?.focused, // Pass the parent's focused record
              event: reloadOn // Include the event that triggered the reload
            })
    if (reloadOn) {
      api.socket.on(reloadOn, async () => {
        await reloadHandler()
        onEvent()
      })
    }

    // EVENTS

    // manage socket room subscription
    if (subscribe) {
      let room = (record) => record[key]
      if (typeof subscribe === 'function') {
        room = subscribe
      }
      watch(focused, (next, prev) => {
        if (prev) {
          debug('unsubscribing')
          api.socket.emit('unsubscribe', room(prev))
        }
        if (next) {
          debug('subscribing')
          api.socket.emit('subscribe', room(next))
        }
      })
    }

    // invalidation
    api.socket.on(`invalidate_${name}`, async ({ type, ids }) => {
      if (!read) {
        throw new Error(
          `${prefix} no 'read' method defined, but 'invalidate_${name}' event was emitted by the backend`
        )
      }
      const focusedId = focused.value ? focused.value[key] : null
      // update or delete
      records.value = records.value
        .map(async (record) => {
          if (ids.include[record[key]]) {
            if (type === 'delete') {
              return null
            } else if (type === 'update') {
              return await read(record[key])
            }
          } else {
            return record
          }
        })
        .filter((record) => !ids.include(record[key]))
      // add fresh data
      if (type === 'create') {
        ids.forEach(async (id) => {
          const record = await read(id)
          records.value.push(record)
        })
      }
      refocus(focusedId)
    })

    // API

    return {
      // data
      list,
      loading,
      // options
      multiselect,
      singleselect,
      // selection
      selected,
      selectedIds,
      isSelected,
      select,
      unselect,
      // focus
      focused,
      focusedId,
      isFocused,
      focus,
      unfocus,
      // children
      name,
      register,
      // api
      read,
      ...wrappedOps
    }
  })
