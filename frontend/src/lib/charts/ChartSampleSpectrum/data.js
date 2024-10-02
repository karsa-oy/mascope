import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { useApp } from '@/stores'
import { api } from '@/api'

export const useChartData = defineStore('chart.sample.spectrum', () => {
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

  watch([() => app.ui.tab.active, () => app.data.peak.list], async ([tab, peaks]) => {
    const activeFileId = app.data.sample.focused?.sample_file_id
    if (activeFileId) {
      if (activeFileId !== loadedFileId.value && tab == 'spectrum') {
        await load(activeFileId, peaks)
        loadedFileId.value = activeFileId
      }
    } else {
      traces.value = []
      loadedFileId.value = null
      if (app.ui.tab.active == 'spectrum') {
        app.ui.tab.active = 'batch'
      }
    }
  })

  async function load(sampleFileId, peaks) {
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
      traces.value = peaks
        .map(({ mz, height, area }) => ({
          name: '',
          type: 'scatter',
          mode: 'lines',
          line: {
            color: 'grey'
          },
          x: [...Array(5).keys()].map(() => mz), // *
          y: [...Array(5).keys()].map((index) => height * (index / 4)), // *
          hovertemplate: [
            '<i>Peak</i>',
            `mz: <b>${mz.toFixed(4)}</b>`,
            `height: <b>${height.toExponential(3)}</b>`,
            `area: <b>${area.toExponential(3)}</b>`
          ].join('<br>')
          // * Plotly's hover tooltip only appears
          // when hovering near a point, so we
          // generate 5 points to make it easy
          // for the user to trigger the tooltop
          // along the whole marker line.
        }))
        .concat({
          name: '',
          line: {
            color: 'rgb(252, 79, 48)'
          },
          mode: 'lines',
          type: 'scatter',
          x: new Float32Array(data.mz),
          y: new Float32Array(data.intensity),
          hovertemplate: ['<i>Signal</i>', 'mz: <b>%{x:.4f}</b>', 'height: <b>%{y:.3e}</b>'].join(
            '<br>'
          )
        })

      length.value = data.intensity.length
    }
    loading.value = false
  }

  return { traces, length, loading }
})
