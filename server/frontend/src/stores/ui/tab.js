import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { useData } from '../data'

const DEFAULT_TAB = 'raw files'

// How long automatic tab switching stays suppressed after a location restore,
// so the restored tab survives the data-driven tab moves that fire as the
// chain streams in (e.g. samples loading forces the 'batch' tab).
const HYDRATE_SETTLE_MS = 2500

export const useTab = defineStore('app.ui.tab', () => {
  const active = ref(DEFAULT_TAB)

  // While hydrating a restored location, the automatic tab watchers below stand
  // down so the tab we are restoring is the final word.
  const hydrating = ref(false)

  const data = useData()

  // When visualized ion unfocused, return to 'batch' if batch exists, else default
  watch(
    () => data.match.visualized.ion,
    (visualized) => {
      if (hydrating.value) return
      if (!visualized && active.value === 'match') {
        active.value = data.batch.focused ? 'batch' : DEFAULT_TAB
      } else if (visualized && active.value !== 'sample') {
        active.value = 'match'
      }
    }
  )

  // Return to 'batch' tab when sample unfocused (if currently on sample tab)
  watch(
    () => data.sample.focused,
    (sample) => {
      if (hydrating.value) return
      if (!sample && active.value === 'sample') {
        active.value = 'batch'
      }
    }
  )
  // Switch to batch tab when samples INITIALLY loaded (0 → N) AND batch focused
  // Leave batch tab when samples become empty
  watch(
    () => data.sample.list.length,
    (length, oldLength) => {
      if (hydrating.value) return
      if (oldLength === 0 && length > 0 && data.batch.focused) {
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
      if (hydrating.value) return
      if (!focused && active.value === 'batch') {
        active.value = DEFAULT_TAB
      }
    }
  )

  return {
    active,
    hydrating,
    default: () => {
      active.value = DEFAULT_TAB
    },
    /**
     * Restore a tab as part of a location apply. Suppresses automatic tab
     * switching for a short settle window so the restored data streaming in
     * does not move the tab away from the one we are restoring.
     */
    hydrate: (tab) => {
      if (!tab) return
      hydrating.value = true
      active.value = tab
      setTimeout(() => {
        hydrating.value = false
      }, HYDRATE_SETTLE_MS)
    }
  }
})
