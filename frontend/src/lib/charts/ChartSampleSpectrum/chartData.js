import { ref, computed, watchEffect } from 'vue'
import { defineStore } from 'pinia'

import { useApp } from '@/stores'
import { api } from '@/api'

export const useChartData = defineStore('sampleSpectrumChartData', () => {
  const traces = ref([])
  const loadedFileId = ref()
  const length = ref()
  const loading = ref(false)

  const app = useApp()

  app.ui.chart.register({
    name: 'ChartSampleSpectrum',
    clear: () => {
      // not needed
    }
  })

  const activeFileId = computed(() => app.data.sample.focused?.sample_file_id)

  watchEffect(async () => {
    if (activeFileId.value) {
      if (activeFileId.value !== loadedFileId.value && app.ui.tab.active == 'spectrum') {
        await load(activeFileId.value)
        loadedFileId.value = activeFileId.value
      }
    } else {
      traces.value = []
      loadedFileId.value = null
      if (app.ui.tab.active == 'spectrum') {
        app.ui.tab.active = 'batch'
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
