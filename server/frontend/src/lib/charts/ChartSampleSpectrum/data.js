import { ref, watchEffect, onMounted } from 'vue'
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

  // load triggering
  watchEffect(async () => {
    const sampleFileId = app.data.sample.focused?.sample_file_id
    const sampleFocused = sampleFileId !== null
    const sampleFileChanged = loadedFileId.value !== sampleFileId
    const peaksLoaded = app.data.peak.list.length > 0
    const tabOpen = app.ui.tab.active === 'spectrum'
    if (sampleFocused && sampleFileChanged && peaksLoaded && tabOpen) {
      await load()
    }
  })

  // unload triggering
  watchEffect(() => {
    const sampleUnfocused = !app.data.sample.focused?.sample_file_id
    if (sampleUnfocused) {
      unload()
    }
  })

  // load spectrum data
  async function load() {
    const sampleFileId = app.data.sample.focused?.sample_file_id
    // start loading
    loading.value = true
    // get spectrum data from the backend
    const data = await api.http.get(`/sample/files/${sampleFileId}/spectrum`, {
      use: 'read',
      type: 'get_spectrum'
    })
    // if successful, construct chart traces
    if (data) {
      traces.value = app.data.peak.list
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
    // wrap up loading
    loading.value = false
    loadedFileId.value = sampleFileId
    return true
  }

  // unload data and switch tab if necessary
  function unload() {
    traces.value = []
    loadedFileId.value = null
    const tabOpen = app.ui.tab.active === 'spectrum'
    if (tabOpen) {
      app.ui.tab.default()
    }
  }

  return { traces, length, unit, loading }
})
