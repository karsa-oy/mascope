import { ref, reactive, computed, watch, watchEffect } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'
import { makeLogger } from '@/lib/logging'
import { runtime } from '@/lib/runtime'

import { useInstrument } from './instrument'

export const useAcquisition = defineStore('app.data.acquisition', () => {
  const instrument = useInstrument()

  const logger = makeLogger({
    prefix: 'data acquisition',
    icon: '🗃️'
  })

  const list = ref([])
  const selected = ref([])
  const focused = computed(() => {
    if (selected.value.length === 1) {
      return selected.value[0]
    } else {
      return null
    }
  })
  const multiselected = computed(() => selected.value.length > 1)
  const unfocus = () => {
    selected.value = []
  }

  const ready = reactive({
    filename: null
  })

  const time = reactive(initTime())
  const days = computed(() =>
    time.mode == 'range' ? null : time.mode == 'Last 24 hours' ? 1 : Number(time.mode.split(' ')[1])
  )
  watchEffect(() => {
    if (time.range.min || time.range.max) {
      time.mode = 'range'
    } else if (time.mode == 'range') {
      time.mode = 'Last 24 hours'
    }
  })
  watch(time, () => unfocus())

  // instrument

  watch(
    computed(() => instrument.focused?.instrument),
    async () => {
      await load()
    }
  )

  watch(
    () => instrument.focused,
    (next, prev) => {
      // clear selection
      unfocus()
      // update socket subscriptions
      if (prev) {
        api.socket.emit('unsubscribe', prev.instrument)
      }
      if (next) {
        api.socket.emit('subscribe', next.instrument)
      }
    }
  )

  // acquisitions

  watch(time, load)

  async function load() {
    if (time.mode.startsWith('Last')) {
      await loadRecent(days.value)
    } else if (time.mode == 'range') {
      await loadRange(time.range)
    }
  }

  async function loadRange(range) {
    const sampleFiles = await api.http.get(`/sample/files`, {
      params: {
        datetime_min: range.min?.toISOString(),
        datetime_max: range.max?.toISOString(),
        instrument: instrument.focused?.instrument,
        sort: 'datetime_utc',
        order: 'asc'
      },
      use: 'read',
      type: 'load_sample_file_range'
    })
    if (sampleFiles) {
      list.value = sampleFiles
    }
  }

  async function loadRecent(days = 7) {
    const recent = await api.http.get(`/sample/files/recent`, {
      params: {
        instrument: instrument.focused?.instrument,
        sort: 'datetime_utc',
        order: 'asc',
        days
      },
      use: 'read',
      type: 'load_recent_sample_files'
    })
    if (recent) {
      list.value = recent
    }
  }

  // Socket event listeners for record updates
  api.socket.on('acquisition_created', (payload) => {
    const { record } = payload

    // Check if this file belongs to the currently focused instrument
    if (record.instrument === instrument.focused?.instrument) {
      // Add to list if within current time filter
      const fileDate = new Date(record.datetime_utc)
      const shouldInclude = (() => {
        if (time.mode.startsWith('Last')) {
          const daysAgo = new Date()
          daysAgo.setDate(daysAgo.getDate() - days.value)
          return fileDate >= daysAgo
        } else if (time.mode === 'range') {
          if (time.range.min && fileDate < time.range.min) return false
          if (time.range.max && fileDate > time.range.max) return false
          return true
        }
        return false
      })()

      if (shouldInclude) {
        list.value = [...list.value, record]
        logger.log(`added ${record.filename}`)
      } else {
        logger.debug(`ignoring ${record.filename} (outside time filter)`)
      }
    }
  })

  api.socket.on('acquisition_updated', (payload) => {
    const { record_id, record } = payload

    // Find and update the acquisition
    const index = list.value.findIndex((f) => f.sample_file_id === record_id)
    if (index >= 0) {
      list.value[index] = record
      logger.log(`updated ${record.filename}`)
    }
  })

  api.socket.on('acquisition_deleted', (payload) => {
    const { record_id } = payload

    // Remove from list if present
    const index = list.value.findIndex((f) => f.sample_file_id === record_id)
    if (index >= 0) {
      const filename = list.value[index].filename
      list.value = list.value.filter((_, i) => i !== index)
      logger.log(`removed ${filename}`)

      // Unfocus if deleted file was selected
      if (selected.value.some((s) => s.sample_file_id === record_id)) {
        unfocus()
      }
    }
  })

  // mz calibration

  const resetFilters = () => {
    selected.value = []
    time.mode = initTime().mode
    time.range = initTime().range
  }

  return {
    // state
    list,
    selected,
    focused,
    multiselected,
    unfocus,
    ready,
    time,
    // actions
    load,
    resetFilters
  }
})

const toDate = (iso) => (iso ? new Date(iso) : null)

function initTime() {
  const configured = runtime.config.acquisition_filter
  if (configured) {
    if (typeof configured == 'string') {
      return {
        mode: configured,
        range: {
          min: null,
          max: null
        }
      }
    } else if (typeof configured == 'object') {
      return {
        mode: 'range',
        range: {
          min: toDate(configured.min),
          max: toDate(configured.max)
        }
      }
    }
  } else {
    return {
      mode: 'Last 24 hours',
      range: {
        min: null,
        max: null
      }
    }
  }
}
