import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { useData } from '../data'

const DEFAULT_TAB = 'acquisitions'

export const useTab = defineStore('app.ui.tab', () => {
  const active = ref(DEFAULT_TAB)

  const data = useData()

  watch(
    () => data.acquisition.mode,
    (measuring) => {
      if (measuring) {
        active.value = 'acquisitions'
      }
    }
  )
  watch(
    () => data.match.visualized.ion,
    (visualized) => {
      if (visualized && active.value !== 'spectrum') {
        active.value = 'match'
      } else {
        if (active.value == 'match') {
          active.value = data.batch.focused ? 'batch' : DEFAULT_TAB
        }
      }
    }
  )
  watch(
    () => data.sample.focused,
    (sample) => {
      if (!sample && active.value == 'spectrum') {
        active.value = 'batch'
      }
    }
  )
  watch(
    () => data.batch.focused,
    (focused) => {
      if (!focused && active.value == 'batch') {
        active.value = DEFAULT_TAB
      }
    }
  )

  return {
    active,
    default: () => {
      active.value = DEFAULT_TAB
    }
  }
})
