<script setup>
import { ref, computed, watch, toRaw } from 'vue'

import ScrollPanel from 'primevue/scrollpanel'
import Tag from 'primevue/tag'

import BaseChartPlotly from '../BaseChartPlotly.vue'

import { BaseMatchTag } from '@/lib/base'
import { clone } from '@/lib/utils'
import { useApp } from '@/stores'

import { useChartData } from './data.js'

const app = useApp()
const data = useChartData()
const plots = ref({})

const { settings } = defineProps({
  settings: {
    type: Object,
    required: true
  }
})

const sampleLength = computed(() => {
  return app.data.sample.selected.length != 1 ? null : app.data.sample.selected[0].length
})

const traces = computed(() => {
  // Scale trace y-values based on "sum / average" toggle
  if (sampleLength === null) return []
  return settings.yMode == 'sum'
    ? data.traces
    : data.traces.map(function (trace) {
        // Scale chart traces by dividing all y-values by sampleLength
        let newTrace = structuredClone(toRaw(trace))
        newTrace.y = trace.y.map((value) => value / sampleLength.value)
        return newTrace
      })
})

// transform raw visualiation data into seperate charts
const isotopeCharts = computed(() => {
  // create an array corresponding to visualized isotopes
  return clone(app.data.match.visualized.isotopes).map((isotope) => {
    // split up the chart's traces by isotope
    const start = traces.value?.findIndex(
      (trace) => trace.target_isotope_id === isotope.target_isotope_id
    )
    const nextStart = traces.value?.findIndex(
      ({ target_isotope_id }, index) => target_isotope_id && index > start
    )
    const end =
      nextStart !== -1 // if next isotope found
        ? nextStart // use it as the end of isotope trace data
        : traces?.length // otherwise use all remaining data
    const isotopeTraces = traces.value?.slice(start, end)
    // compute match category for this isotope
    let match_category = 0
    if (isotope.match_score > app.data.match.params.current.possible_match_threshold) {
      match_category = 1
    }
    if (isotope.match_score > app.data.match.params.current.probable_match_threshold) {
      match_category = 2
    }
    // return chart data
    return {
      // all match isotope fields
      ...isotope,
      // and our computed data
      traces: isotopeTraces,
      match_category
    }
  })
})

// auto vs manual scale
const scale = computed(
  () =>
    settings.intensityScale // if user set the scale
      ? { range: [0, settings.intensityScale] } // use set scale
      : {} // otherwise auto set scale
)
// standard plotly layout
const layout = computed(() => ({
  yaxis: {
    title: `Signal intensity [${data?.unit}${settings.yMode == 'sum' ? '' : '/s'}]`,
    gridcolor: '#33333399',
    rangemode: 'nonnegative',
    ...scale.value
  },
  xaxis: {
    title: 'm/z [Th]',
    gridcolor: '#33333399'
  },
  dragmode: 'zoom',
  showlegend: false,
  height: '300',
  width: '450'
}))

const area = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 0
})
const error = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

// reset chart zoom when changing targets
watch(
  // follow visualization, not focused target
  () => app.data.match.visualized.ion.target_ion_id,
  (visualized) => {
    // reset zoom for all isotope charts
    isotopeCharts.value.forEach((_, index) => {
      // use isotope index to preserve chart
      // correspondence between position & zoom
      const plot = plots.value[index]
      if (visualized && plot) {
        console.log('[chart] resetting match spectra zoom')
        plot.resetZoom()
      }
    })
  }
)
</script>

<template>
  <div>
    <ScrollPanel>
      <div class="row" style="gap: 1rem; justify-content: flex-start; padding: 0 2rem">
        <figure
          v-for="(isotopeChart, index) of isotopeCharts"
          :key="isotopeChart.target_isotope_id"
        >
          <h3 :style="`color: ${isotopeChart.traces[0]?.line.color}; margin: 0`">
            Isotope {{ error.format(isotopeChart.mz) }}
          </h3>
          <!--
            This chart uses a *function ref* to enable dynamically
            assigning refs to a reactive object. We use the `index`
            rather than the `target_isotope_id` to ensure that we
            can persist or reset zoom correctly as we switch targets
            and samples.

            See https://vuejs.org/guide/essentials/template-refs.html#function-refs
          -->
          <BaseChartPlotly
            :id="`ChartMatchSpectrum-${isotopeChart.target_isotope_id}`"
            :title="`Isotope ${error.format(isotopeChart.mz)}`"
            :ref="(el) => (plots[index] = el)"
            :data="isotopeChart.traces"
            :layout="layout"
            hideTitle
          />
          <div
            id="chart-spectrum-controls"
            class="row"
            style="flex-wrap: wrap; max-width: 35ch; justify-content: center"
          >
            <BaseMatchTag :row="isotopeChart" text />
            <Tag
              :value="`Peak intensity: ${area.format(settings.yMode == 'sum' ? isotopeChart.sample_peak_area : isotopeChart.sample_peak_area / sampleLength)}`"
              :severity="
                isotopeChart.sample_peak_area < app.data.match.params.current.peak_min_intensity
                  ? 'warn'
                  : 'info'
              "
            />
            <Tag
              :value="`mz error: ${error.format(isotopeChart.match_mz_error)}`"
              :severity="
                Math.abs(isotopeChart.match_mz_error) > app.data.match.params.current.mz_tolerance
                  ? 'warn'
                  : 'info'
              "
            />

            <Tag
              :value="`Abundance error: ${error.format(isotopeChart.match_abundance_error)}`"
              :severity="
                Math.abs(isotopeChart.match_abundance_error) >
                app.data.match.params.current.isotope_ratio_tolerance
                  ? 'warn'
                  : 'info'
              "
            />
          </div>
        </figure>
      </div>
    </ScrollPanel>
  </div>
</template>

<style scoped>
#chart-spectrum-controls :global(fieldset) {
  margin: 0 !important;
}
</style>
