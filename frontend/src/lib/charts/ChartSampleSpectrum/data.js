import { ref, computed, watchEffect } from 'vue'
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
      traces.value = app.data.peak.list
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
