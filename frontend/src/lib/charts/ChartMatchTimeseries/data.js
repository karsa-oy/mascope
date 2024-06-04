import { ref } from 'vue'
import { defineStore } from 'pinia'

import { useDashboard } from '@/stores'

export const useData = defineStore('matchTimeseriesChartData', () => {
  const traces = ref([])
  const length = ref()

  const dashboard = useDashboard()
  dashboard.register({
    name: 'ChartMatchSpectra',
    clear: () => {
      traces.value = []
      length.value = 0
    }
  })

  async function onVisualizationSignalTimeseries(payload) {
    for (let trace of payload) {
      length.value = trace.x.length
      trace.x = new Float32Array(trace.x)
      trace.y = new Float32Array(trace.y)
    }
    traces.value = [...traces.value, ...payload]
  }
  return { traces, onVisualizationSignalTimeseries, length }
})
