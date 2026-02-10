import { ref, shallowRef, watch, watchEffect, computed } from 'vue'
import { defineStore } from 'pinia'

import { useApp } from '@/stores'
import { api } from '@/api'
import { usePreview } from '@/lib/panes'

export const useChartData = defineStore('chart.sample.spectrum', () => {
  const spectrumData = shallowRef(null)
  const length = ref()
  const unit = ref('')
  const loading = ref(false)

  const app = useApp()
  const preview = usePreview()

  app.ui.chart.register({
    name: 'ChartSampleSpectrum',
    clear: () => {
      // not needed
    }
  })

  // Watch for sample change - clear data and reset chart
  watch(
    () => app.data.sample.focusedId,
    (sampleId, oldSampleId) => {
      if (sampleId !== oldSampleId) {
        console.debug('🔄 [chart.sample.spectrum] sample changed - resetting chart')
        unload()
      }
      if (sampleId) {
        load()
      }
    }
  )

  const gl = ''

  // load spectrum data
  async function load() {
    const sampleItemId = app.data.sample.focusedId
    // start loading
    loading.value = true
    // get spectrum data from the backend
    spectrumData.value = await api.http.get(`/samples/${sampleItemId}/spectrum`, {
      use: 'read',
      type: 'get_spectrum'
    })

    unit.value = spectrumData.value.intensity_unit
    length.value = spectrumData.value.intensity.length
    loading.value = false
  }

  const mainTraces = computed(() => {
    const traces = []
    // add spectrum trace
    if (spectrumData.value) {
      traces.push({
        name: 'Signal',
        line: {
          color: 'green'
        },
        mode: 'lines',
        type: 'scatter' + gl,
        x: new Float32Array(spectrumData.value.mz),
        y: new Float32Array(spectrumData.value.intensity),
        hovertemplate:
          ['<i>Signal</i>', 'm/z: <b>%{x:.4f}</b>', `intensity: <b>%{y:.3e}</b>`].join('<br>') +
          '<extra></extra>' // use "<extra></extra>" to get rid of extra block from the hoverbox
      })
    }
    // add peak traces
    if (!app.data.peak.pending && app.data.peak.list.length > 0) {
      traces.push({
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
      })
    }
    return traces
  })

  const focusTrace = computed(() => {
    const focused = app.data.peak.focused
    return focused
      ? [
          {
            name: 'Focused Peak',
            type: 'scatter' + gl,
            mode: 'lines+markers',
            line: {
              color: '#fb8f74'
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
              (index) =>
                (preview.peak.relative_abundance / preview.peak.abundance_reference) *
                preview.peak.intensity_reference *
                (index / 2)
            ),
            hovertemplate: ['<i>Peak</i>', 'mz: <b>%{x:.4f}</b>'].join('<br>') + '<extra></extra>'
          }
        ]
      : []
  )

  const traces = computed(() => [...mainTraces.value, ...focusTrace.value, ...previewTrace.value])

  // unload data and switch tab if necessary
  function unload() {
    spectrumData.value = null
  }

  return { traces, length, unit, loading }
})
