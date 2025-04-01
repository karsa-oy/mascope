import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { useApp } from '@/stores'

export const usePreview = defineStore('peakAssign.preview', () => {
  const app = useApp()

  const peak = ref()

  // autoclear selected the preview peak when the focused peak is changed
  watch(
    () => app.data.peak.focusedId,
    () => {
      peak.value = null
    }
  )

  return {
    peak
  }
})
