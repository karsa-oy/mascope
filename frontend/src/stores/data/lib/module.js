import { ref, computed, watch, onMounted } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

export const defineModule = ({
  name, // module name (snake_case)
  key, // data key (normally id)
  subscribe = false, // socket io subscription
  useParent = null, // optional parent module
  multiselect = false, // enable multiselection
  autofocus = false, // focused first element on load
  reloadSelfOn = null, // events to reload the module on
  reloadChildrenOn = null, // events to reload child modules on
  // api
  load, // async func, may accept parent record
  read, // get one record by id
  ...ops // other operations optional
}) =>
  defineStore(`app.data.${name.replaceAll('_', '.')}`, () => {
    // CONFIG

    const prefix = `[app.data.${name.replaceAll('_', ' ')}]`
    const log = (message) => console.log(`${prefix} ${message}`)

    const singleselect = !multiselect
    const parent = useParent ? useParent() : null

    if (parent && parent.multiselect) {
      throw new Error(`${prefix} parent module parent (${parent.name}) cannot be multiselectable`)
    }

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
          if (!active(arg)) {
            focused.value = records.value.find((record) => record[key] == arg[key])
          }
        }
    const unfocus = multiselect
      ? (arg) => {
          if (active(arg)) {
            selected.value = []
          }
        }
      : // singleselect
        (arg) => {
          if (active(arg)) {
            focused.value = null
          }
        }
    const clear = multiselect
      ? () => {
          selected.value = []
        }
      : // singleselect
        () => {
          focused.value = null
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
    const reload = async (parent) => {
      log(`load triggered by ${parent?.name ?? 'mount'}`)
      loading.value = true
      if (parent) {
        records.value = parent?.focusedId ? await load(parent.focusedId) : []
      } else {
        records.value = await load()
      }
      records.value.forEach((record, index) => (record.index = (index + 1).toString()))
      log('data loaded')
      if (selected.value.length > 0) {
        clear()
        log('selection cleared')
      }
      if (autofocus && records.value.length > 0) {
        focus(records.value[0])
      }
      // propegate to children
      if (children.value.length > 0) {
        const focusedId = focused.value ? focused.value[key] : null
        await Promise.all(children.value.map(({ reload }) => reload({ name, focusedId })))
        log('child data loaded')
      }
      loading.value = false
    }

    // load on init
    if (!parent) {
      // root modules self init on mount
      onMounted(() => reload())
    } else {
      // child modules init with parent
      parent.register({ reload })
    }

    // reload children on refocus
    if (singleselect) {
      watch(
        computed(() => (focused.value ? focused.value[key] : null)),
        (focusedId) => {
          children.value.forEach(({ reload }) =>
            reload({
              name,
              focusedId
            })
          )
        }
      )
    }

    // event triggered reloading

    if (!parent) {
      api.socket.on(`org_reload`, reload)
    } else {
      if (parent.reloadChildrenOn) {
        api.socket.on(parent.reloadChildrenOn, reload)
      }
    }
    if (reloadSelfOn) {
      api.socket.on(reloadSelfOn, reload)
    }

    // EVENTS

    // manage socket room subscription
    if (subscribe) {
      watch(focused, (next, prev) => {
        if (prev) {
          api.emit('unsubscribe', prev[key])
        }
        if (next) {
          api.emit('subscribe', next[key])
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
      // refocus
      const focusValid = focusedId && records.value.map((record) => record[key]).includes(focusedId)
      const defaultId = singleselect ? records.value[0] : null
      const id = focusValid ? focusedId : defaultId
      if (id) {
        focus({ [key]: id })
      } else {
        unfocus()
      }
    })

    // API

    return {
      // data
      list,
      loading,
      // options
      multiselect,
      singleselect,
      reloadChildrenOn,
      // selection
      selected,
      focused,
      active,
      select,
      unselect,
      focus,
      unfocus,
      clear,
      // children
      name,
      register,
      // api
      read,
      ...ops
    }
  })
