import { ref, shallowRef, watch, computed } from 'vue'
import { defineStore } from 'pinia'

import { useApp } from '@/stores'
import { api } from '@/api'
import { usePreview } from '@/lib/panes'

// Peak coloring by confidence tier for the annotated spectrum. One Plotly trace
// per tier; role reagent/artifact is grouped separately (orthogonal to tier).
const TIER_TRACES = [
  { key: 'identified', name: 'Identified', color: '#1f9d63' },
  { key: 'candidate', name: 'Candidate', color: '#d99a2b' },
  { key: 'below_assignability', name: 'Below assignability', color: '#8a94a6' },
  { key: 'reagent', name: 'Reagent / artifact', color: '#8a5ed0' },
  { key: 'unassigned', name: 'Unassigned', color: 'grey' }
]

// Which tier bucket a peak falls in, given the run's assignments.
function bucketOf(assignments, peak) {
  const assignment = assignments.forPeak(peak.peak_id)
  if (!assignment) return 'unassigned'
  if (assignment.role === 'reagent' || assignment.role === 'artifact') return 'reagent'
  const tier = assignment.tier
  return tier === 'identified' || tier === 'candidate' || tier === 'below_assignability'
    ? tier
    : 'unassigned'
}

// Build a vertical-stick Plotly trace for a set of peaks. Three points per peak
// (0 -> height -> gap) so the hover tooltip triggers along the whole marker.
// customdata carries [height, area, mz, formula]; [height, area] also lets
// ChartSampleSpectrum rescale for "average" instead of "sum".
function peakTrace(name, color, peaks, assignments = null) {
  return {
    name,
    type: 'scatter',
    mode: 'lines',
    line: { color },
    x: peaks.map(({ mz }) => [mz, mz, null]).flat(),
    y: peaks.map(({ height }) => [0, height, null]).flat(),
    customdata: peaks
      .map((peak) => {
        const formula = assignments?.forPeak(peak.peak_id)?.assigned_formula ?? ''
        const point = [peak.height, peak.area, peak.mz, formula]
        return [point, point, null]
      })
      .flat(),
    hovertemplate:
      [
        `<i>${name}</i>`,
        'mz: <b>%{customdata[2]:.4f}</b>',
        assignments ? 'formula: <b>%{customdata[3]}</b>' : null,
        'height: <b>%{customdata[0]:.3e}</b>',
        'area: <b>%{customdata[1]:.3e}</b>'
      ]
        .filter(Boolean)
        .join('<br>') + '<extra></extra>'
  }
}

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
    // add peak traces, colored by assignment tier
    if (!app.data.peak.pending && app.data.peak.list.length > 0) {
      const assignments = app.data.peakAssignment.peak
      if (!assignments.run) {
        // No assignment run: keep the original single grey peak trace.
        traces.push(peakTrace('Peak', 'grey', app.data.peak.list))
      } else {
        // Annotated spectrum: one trace per confidence tier.
        for (const { key, name, color } of TIER_TRACES) {
          const peaks = app.data.peak.list.filter((peak) => bucketOf(assignments, peak) === key)
          if (peaks.length > 0) traces.push(peakTrace(name, color, peaks, assignments))
        }
      }
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
