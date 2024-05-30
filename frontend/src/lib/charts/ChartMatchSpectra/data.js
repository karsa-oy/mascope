import { ref } from 'vue'
import { defineStore } from 'pinia'

import { useDashboard, useFocusedMatch } from '@/stores'

export const useData = defineStore('matchSpectraChartData', () => {
  const traces = ref([])

  const dashboard = useDashboard()
  dashboard.register({
    name: 'ChartMatchSpectra',
    clear: () => {
      traces.value = []
    }
  })

  async function onVisualizationSignalSumSpectrum(payload) {
    const match = useFocusedMatch()
    for (let trace of payload) {
      trace.x = new Float32Array(trace.x)
      trace.y = new Float32Array(trace.y)

      // Check if the trace has target_isotope_id and update the corresponding isotope in activeIsotopes
      if (trace.target_isotope_id) {
        const isotope = match.isotopes.find(
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
  }
  return { traces, onVisualizationSignalSumSpectrum }
})
