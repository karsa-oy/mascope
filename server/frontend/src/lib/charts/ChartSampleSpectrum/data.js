import { ref, shallowRef, watchEffect, computed } from 'vue'
import { defineStore } from 'pinia'

import { useApp } from '@/stores'
import { api } from '@/api'
import { usePreview } from '@/lib/panes'

export const useChartData = defineStore('chart.sample.spectrum', () => {
  const mainTraces = shallowRef([])
  const loadedFileId = ref()
  const length = ref()
  const unit = ref('')
  const pending = ref()
  const loading = ref(false)
  const mzRangeMax = ref()

  const app = useApp()
  const preview = usePreview()

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
      load()
    }
  })

  // unload triggering
  watchEffect(() => {
    const sampleUnfocused = !app.data.sample.focused?.sample_file_id
    if (sampleUnfocused) {
      unload()
    }
  })

  const gl = ''

  // load spectrum data
  async function load() {
    const sampleItemId = app.data.sample.focused?.sample_item_id
    // start loading
    loading.value = true
    // get spectrum data from the backend
    const data = await api.http.get(`/samples/${sampleItemId}/spectrum`, {
      use: 'read',
      type: 'get_spectrum'
    })

    mzRangeMax.value = (mz, dmz) => {
      const from = data.mz.findLastIndex((val) => val < mz - dmz)
      const to = data.mz.findIndex((val) => val > mz + dmz)
      const intensities = data.intensity.slice(from, to + 1)
      return Math.max(...intensities)
    }
    mainTraces.value = [
      {
        name: 'Peak',
        type: 'scatter' + gl,
        mode: 'lines',
        line: {
          color: 'grey'
        },
        x: app.data.peak.list.map(({ mz }) => [mz, mz, null]).flat(), // *
        y: app.data.peak.list.map(({ height }) => [0, height, null]).flat(), // *
        customdata: app.data.peak.list
          .map(({ height, area, mz }) => [[height, area, mz], [height, area, mz], null])
          .flat(), // **
        hovertemplate:
          [
            '<i>Peak</i>',
            'mz: <b>%{customdata[2]:.4f}</b>',
            'height: <b>%{customdata[0]:.3e}</b>',
            'area: <b>%{customdata[1]:.3e}</b>'
          ].join('<br>') + '<extra></extra>' // use "<extra></extra>" to get rid of extra block from the hoverbox
        // * Plotly's hover tooltip only appears
        // when hovering near a point, so we
        // generate 3 points to make it easy
        // for the user to trigger the tooltop
        // along the whole marker line.

        // ** Add [height, area] into "customdata" to enable
        // access in ChartSampleSpectrum when scaling for
        // "average" instead of "sum".
      },
      {
        name: 'Signal',
        line: {
          color: 'green'
        },
        mode: 'lines',
        type: 'scatter' + gl,
        x: new Float32Array(data.mz),
        y: new Float32Array(data.intensity),
        hovertemplate:
          ['<i>Signal</i>', 'm/z: <b>%{x:.4f}</b>', `intensity: <b>%{y:.3e}</b>`].join('<br>') +
          '<extra></extra>' // use "<extra></extra>" to get rid of extra block from the hoverbox
      }
    ]
    unit.value = data.intensity_unit
    length.value = data.intensity.length
    loading.value = false
  }
  const focusTrace = computed(() => {
    const focused = app.data.peak.focused
    return focused
      ? [
          {
            name: 'Focused Peak',
            type: 'scatter' + gl,
            mode: 'lines+markers',
            line: {
              color: 'white'
            },
            x: [focused.mz, focused.mz], // *
            y: [0, focused.height], // *
            customdata: [
              [focused.height, focused.area, focused.mz],
              [focused.height, focused.area, focused.mz]
            ],
            hovertemplate:
              [
                '<i>Peak</i>',
                'mz: <b>%{customdata[2]:.4f}</b>',
                'height: <b>%{customdata[0]:.3e}</b>',
                'area: <b>%{customdata[1]:.3e}</b>'
              ].join('<br>') + '<extra></extra>'
          }
        ]
      : []
  })
  const previewTrace = computed(() =>
    preview.peak
      ? [
          {
            name: 'Peak Preview',
            line: {
              color: 'red'
            },
            mode: 'lines',
            type: 'scatter' + gl,
            x: [...Array(3).keys()].map(() => preview.peak.mz), // *
            y: [...Array(3).keys()].map(
              (index) => mzRangeMax.value(preview.peak.mz, 0.05) * (index / 2)
            ),
            hovertemplate: ['<i>Peak</i>', 'mz: <b>%{x:.4f}</b>'].join('<br>') + '<extra></extra>'
          }
        ]
      : []
  )
  const traces = computed(() => [...mainTraces.value, ...focusTrace.value, ...previewTrace.value])

  // unload data and switch tab if necessary
  function unload() {
    traces.value = []
    loadedFileId.value = null
    const tabOpen = app.ui.tab.active === 'spectrum'
    if (tabOpen) {
      app.ui.tab.default()
    }
  }

  return { traces, length, unit, loading, mzRangeMax }
})
