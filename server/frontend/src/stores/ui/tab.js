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
  // Switch to batch tab when samples loaded AND batch focused
  // Leave batch tab when samples become empty
  watch(
    () => data.sample.list.length,
    (length) => {
      if (length > 0 && data.batch.focused) {
        // Samples loaded + batch focused → enter batch tab
        active.value = 'batch'
      } else if (length === 0 && active.value === 'batch') {
        // Samples empty → leave batch tab
        active.value = DEFAULT_TAB
      }
    }
  )

  // Return to default tab when batch unfocused (if currently on batch tab)
  watch(
    () => data.batch.focused,
    (focused) => {
      if (!focused && active.value === 'batch') {
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
