import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { useData } from '../data'

const DEFAULT_TAB = 'acquisitions'

export const useTab = defineStore('app.ui.tab', () => {
  const active = ref(DEFAULT_TAB)

  const data = useData()

  // Switch to 'match' tab when visualized ion focused (unless on spectrum tab)
  // When visualized ion unfocused, return to 'batch' if batch exists, else default
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

  // Return to 'batch' tab when sample unfocused (if currently on spectrum tab)
  watch(
    () => data.sample.focused,
    (sample) => {
      if (!sample && active.value == 'spectrum') {
        active.value = 'batch'
      }
    }
  )
  // Switch to 'batch' tab when collection focused, return to default when unfocused
  watch(
    () => data.match.collection.focused,
    (focused, unfocused) => {
      if (focused && data.batch.focused && data.sample.list.length > 0) {
        // Collection focused + batch loaded + has samples → switch to batch tab
        active.value = 'batch'
      } else if (!focused && unfocused && active.value === 'batch') {
        // Collection unfocused → leave batch tab
        active.value = DEFAULT_TAB
      }
    }
  )
  // Return to default tab when batch unfocused (if currently on batch tab)
  watch(
    () => data.batch.focused,
    (focused) => {
      if (!focused && active.value == 'batch') {
        active.value = DEFAULT_TAB
      }
    }
  )

  // Guard: switch away from batch tab if sample list becomes empty
  watch(
    () => data.sample.list.length,
    (length) => {
      if (length === 0 && active.value === 'batch') {
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
