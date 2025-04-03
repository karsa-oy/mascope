import { ref } from 'vue'
import { defineStore } from 'pinia'

import { useApp } from '@/stores'

import { api } from '@/api'

export const useChartData = defineStore('chart.match.spectra', () => {
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

  api.socket.on('visualization_signal_sum_spectrum', (payload) => {
    for (let trace of payload) {
      length.value = length.value + trace.x.length
      unit.value = trace.unit ? trace.unit : unit.value
      trace.x = new Float32Array(trace.x)
      trace.y = new Float32Array(trace.y)

      // Check if the trace has target_isotope_id and update the corresponding isotope in activeIsotopes
      if (trace.target_isotope_id) {
        const isotope = app.data.match.visualized.isotopes?.find(
          (iso) => iso.target_isotope_id === trace.target_isotope_id
        )
        if (isotope) {
          // Extract RGB values and convert them to the 0-255 range
          const colorParts = trace.line.color.match(/(\d+\.?\d*)/g)
          if (colorParts) {
            const r = Math.round(parseFloat(colorParts[0]) * 255)
            const g = Math.round(parseFloat(colorParts[1]) * 255)
            const b = Math.round(parseFloat(colorParts[2]) * 255)
            isotope.color = `rgb(${r},${g},${b})`
          }
        }
      }
    }
    traces.value = [...traces.value, ...payload]
  })
  return { traces, length, unit }
})
