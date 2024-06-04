import { ref, computed, watchEffect } from 'vue'
import { defineStore } from 'pinia'

import { useDashboard, useSampleStore } from '@/stores'
import { api } from '@/api'

export const useData = defineStore('sampleSpectrumChartData', () => {
  const traces = ref([])
  const loadedFileId = ref()
  const length = ref()
  const loading = ref(false)

  const dashboard = useDashboard()
  const sampleStore = useSampleStore()

  dashboard.register({
    name: 'ChartSampleSpectrum',
    clear: () => {
      // not needed
    }
  })

  const activeFileId = computed(() => sampleStore.active?.sample_file_id)

  watchEffect(async () => {
    if (activeFileId.value) {
      if (activeFileId.value !== loadedFileId.value && dashboard.tab == 'spectrum') {
        await load(activeFileId.value)
        loadedFileId.value = activeFileId.value
      }
    } else {
      traces.value = []
      loadedFileId.value = null
      if (dashboard.tab == 'spectrum') {
        dashboard.tab = 'batch'
      }
    }
  })

  async function load(sampleFileId) {
    loading.value = true
    const data = (
      await api.request.read({
        method: 'getSampleSpectrum',
        body: {
          sample_file_id: sampleFileId
        }
      })
    )?.data
    if (data) {
      traces.value = [
        {
          name: 'spectrum',
          line: {
            color: 'rgb(252, 79, 48)'
          },
          mode: 'lines',
          type: 'scatter',
          x: new Float32Array(data.mz),
          y: new Float32Array(data.intensity)
        }
      ]
      length.value = data.intensity.length
    }
    loading.value = false
  }

  return { traces, length, loading }
})
