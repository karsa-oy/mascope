import { ref } from 'vue'
import { defineStore } from 'pinia'

import { useDashboard } from '@/stores'

export const useData = defineStore('matchTimeseriesChartData', () => {
  const traces = ref([])

  const dashboard = useDashboard()
  dashboard.register({
    name: 'ChartMatchSpectra',
    clear: () => {
      traces.value = []
    }
  })

  async function onVisualizationSignalTimeseries(payload) {
    for (let trace of payload) {
      trace.x = new Float32Array(trace.x)
      trace.y = new Float32Array(trace.y)
    }
    traces.value = [...traces.value, ...payload]
  }
  return { traces, onVisualizationSignalTimeseries }
})
