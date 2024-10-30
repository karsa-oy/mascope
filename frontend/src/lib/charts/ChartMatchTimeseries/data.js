import { ref } from 'vue'
import { defineStore } from 'pinia'

import { useApp } from '@/stores'
import { api } from '@/api'

export const useChartData = defineStore('chart.match.timeseries', () => {
  const traces = ref([])
  const length = ref()
  const unit = ref('')

  const app = useApp()

  app.ui.chart.register({
    name: 'ChartMatchSpectra',
    clear: () => {
      traces.value = []
      length.value = 0
    }
  })

  api.socket.on('visualization_signal_timeseries', (payload) => {
    for (let trace of payload) {
      length.value = trace.x.length
      unit.value = trace.unit ? trace.unit : unit.value
      trace.x = new Float32Array(trace.x)
      trace.y = new Float32Array(trace.y)
    }
    traces.value = [...traces.value, ...payload]
  })
  return { traces, length, unit }
})
