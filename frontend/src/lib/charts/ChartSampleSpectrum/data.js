import { ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { useApp } from '@/stores'
import { api } from '@/api'

export const useChartData = defineStore('chart.sample.spectrum', () => {
  const traces = ref([])
  const loadedFileId = ref()
  const length = ref()
  const unit = ref('')
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
    const data = await api.http.get(`/sample/files/${sampleFileId}/spectrum`, {
      use: 'read',
      type: 'get_spectrum'
    })
    if (data) {
      traces.value = peaks
        .map(({ mz, height, area }) => ({
          name: 'Peak',
          type: 'scatter',
          mode: 'lines',
          line: {
            color: 'grey'
          },
          x: [...Array(3).keys()].map(() => mz), // *
          y: [...Array(3).keys()].map((index) => height * (index / 2)), // *
          customdata: [...Array(3).keys()].map(() => [height, area]), // **
          hovertemplate:
            [
              '<i>Peak</i>',
              `mz: <b>${mz.toFixed(4)}</b>`,
              `height: <b>%{customdata[0]:.3e}</b>`,
              `area: <b>%{customdata[1]:.3e}</b>`
            ].join('<br>') + '<extra></extra>' // use "<extra></extra>" to get rid of extra block from the hoverbox
          // * Plotly's hover tooltip only appears
          // when hovering near a point, so we
          // generate 3 points to make it easy
          // for the user to trigger the tooltop
          // along the whole marker line.

          // ** Add [height, area] into "customdata" to enable
          // access in ChartSampleSpectrum when scaling for
          // "average" instead of "sum".
        }))
        .concat({
          name: 'Signal',
          line: {
            color: 'rgb(252, 79, 48)'
          },
          mode: 'lines',
          type: 'scatter',
          x: new Float32Array(data.mz),
          y: new Float32Array(data.intensity),
          hovertemplate:
            ['<i>Signal</i>', 'm/z: <b>%{x:.4f}</b>', `intensity: <b>%{y:.3e}</b>`].join('<br>') +
            '<extra></extra>' // use "<extra></extra>" to get rid of extra block from the hoverbox
        })
      unit.value = data.intensity_unit
      length.value = data.intensity.length
    }
    loading.value = false
  }

  return { traces, length, unit, loading }
})
