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
  unfocusBefore = [], // unofucus before running these ops
  multiselect = false, // ⚠️ currently not in use
  // api
  load, // async func, may accept parent record
  read, // get one record by id
  ...ops // other operations optional
}) =>
  defineStore(`app.data.${name.replaceAll('_', '.')}`, () => {
    // CONFIG

    const prefix = `[app.data.${name.replaceAll('_', ' ')}]`
    const log = (message, ...rest) => console.log(`${prefix} ${message}`, ...rest)

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
      : computed(() => (selected.value?.length == 1 ? selected.value[0] : null))
    const focusedId = computed(() => (focused.value ? focused.value[key] : null))
    const active = (arg) =>
      arg ? selected.value.map((record) => record[key]).includes(arg[key]) : false

    // methods
    const select = multiselect
      ? (...args) => {
          args.forEach((arg) => {
            if (!active(arg)) {
              selected.value.push(records.value.find((record) => record[key] == arg[key]))
            }
          })
        }
      : // singleselect
        (arg) => {
          if (!active(arg)) {
            focused.value = records.value.find((record) => record[key] == arg[key])
          }
        }
    const unselect = multiselect
      ? (...args) => {
          args.forEach((arg) => {
            if (active(arg)) {
              selected.value = selected.value.filter((record) => record[key] !== arg[key])
            }
          })
        }
      : // singleselect
        (arg) => {
          if (active(arg)) {
            focused.value = null
          }
        }
    const focus = multiselect
      ? (arg) => {
          if (!active(arg)) {
            selected.value = [records.value.find((record) => record[key] == arg[key])]
          }
        }
      : // singleselect
        (arg) => {
          if (typeof arg === 'function') {
            // allow predicates to focus with arbitrary conditions
            focused.value = records.value.find(arg)
          } else {
            // but normally, focus using a record or key field
            if (!active(arg)) {
              focused.value = records.value.find((record) => record[key] == arg[key])
            }
          }
        }
    const unfocus = multiselect
      ? (arg) => {
          if (arg) {
            if (active(arg)) {
              selected.value = []
            }
          } else {
            selected.value = []
          }
        }
      : // singleselect
        (arg) => {
          if (arg) {
            if (active(arg)) {
              focused.value = null
            }
          } else {
            focused.value = null
          }
        }
    // internal
    const refocus = (focusedId) => {
      if (focusedId) {
        // refocus
        const focusValid = records.value.map((record) => record[key]).includes(focusedId)
        const id = focusValid ? focusedId : null
        if (id) {
          focus({ [key]: id })
        } else {
          unfocus()
        }
      }
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
      log(`load triggered by ${trigger?.event ?? trigger?.name ?? 'mount'}`)
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
        log('child data loaded')
      }
      loading.value = false
    }

    // load on init
    onMounted(() => {
      const auth = useAuth()
      auth.onLogin(() => {
        if (!parent) {
          // root modules self init on mount
          reload()
        }
      })
    })

    if (parent) {
      // child modules init with parent
      parent.register({ reload })
    }

    // reload children on refocus
    watch(focused, (focused) => {
      children.value.forEach(({ reload }) =>
        reload({
          name,
          focused
        })
      )
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
    if (reloadOn) {
      api.socket.on(
        reloadOn,
        // Check if the parent is a virtual parent (used for special cases like match data)
        parent && parent.name.includes('virtual')
          ? reload // For virtual parents, reload without passing trigger arguments
          : () =>
              reload({
                name: parent?.name,
                focused: parent?.focused, // Pass the parent's focused record
                event: reloadOn // Include the event that triggered the reload
              })
      )
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
          log('unsubscribing')
          api.socket.emit('unsubscribe', room(prev))
        }
        if (next) {
          log('subscribing')
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
            if (type == 'delete') {
              return null
            } else if (type == 'update') {
              return await read(record[key])
            }
          } else {
            return record
          }
        })
        .filter((record) => !ids.include(record[key]))
      // add fresh data
      if (type == 'create') {
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
      focused,
      focusedId,
      active,
      select,
      unselect,
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
