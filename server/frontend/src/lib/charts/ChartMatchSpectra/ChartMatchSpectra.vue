<script setup>
import { ref, computed, watch, toRaw } from 'vue'

import { useWindowSize } from '@vueuse/core'

import ScrollPanel from 'primevue/scrollpanel'
import Tag from 'primevue/tag'

import { BaseMatchTag } from '@/lib/base'
import { clone } from '@/lib/utils'
import { num } from '@/lib/formatters'
import { useApp } from '@/stores'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useChartData } from './data.js'

const app = useApp()
const data = useChartData()

const { height, width } = useWindowSize()

const plots = ref({})

const { settings } = defineProps({
  settings: {
    type: Object,
    required: true
  },
  sidebarOpen: {
    type: Boolean,
    required: true
  }
})

const sampleLength = computed(() =>
  app.data.sample.selected.length != 1 ? null : app.data.sample.selected[0].length
)

const traces = computed(() => {
  // Scale trace y-values based on "average / sum" toggle
  if (sampleLength === null) {
    return []
  }
  return settings.yMode == 'average'
    ? data.traces
    : data.traces.map((trace) => {
        // Scale chart traces by multiplying all y-values by sampleLength
        let newTrace = structuredClone(toRaw(trace))
        newTrace.y = trace.y.map((value) => value * sampleLength.value)
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
    // compute match category with UI match params
    const match_category = app.data.match.params.uiCategory(isotope)
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
    title: `Signal intensity [${settings.yMode == 'average' ? 'counts/s' : 'counts'}]`,
    gridcolor: '#33333399',
    rangemode: 'nonnegative',
    ...scale.value
  },
  xaxis: {
    title: 'm/z [Th]',
    gridcolor: '#33333399'
  },
  margin: { l: 50, r: 5, t: 30, b: 40 },
  dragmode: 'zoom',
  showlegend: false,
  height: 250,
  width: (width * (app.ui.split.right / 100)) / isotopeCharts.value.length
}))

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
        console.log('📊 [chart] resetting match spectra zoom')
        plot.resetZoom()
      }
    })
  }
)
</script>

<template>
  <div>
    <div
      class="row"
      :style="`
          gap: 0rem;
          align-items: flex-start;
          justify-content: flex-start;
          max-width: calc(${app.ui.split.right}vw - 4rem);
          height: 300px;
        `"
    >
      <figure
        v-for="(isotopeChart, index) of isotopeCharts"
        :key="isotopeChart.target_isotope_id"
        :style="`
            width: calc(${app.ui.split.right}vw / ${isotopeCharts.length} - 2rem);
            height: calc((100vh - 40rem) / 2);
            position: relative;
          `"
        :class="sidebarOpen ? 'sidebarOpen' : ''"
      >
        <h3 :style="`color: ${isotopeChart.traces[0]?.line.color}; margin: 0`">
          <BaseMatchTag :row="isotopeChart" />
          Isotope {{ num.mz.format(isotopeChart.mz) }}
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
          :title="`Isotope ${num.mz.format(isotopeChart.mz)}`"
          :ref="(el) => (plots[index] = el)"
          :data="isotopeChart.traces"
          :layout="layout"
          hideTitle
        />
        <div class="float">
          <Tag
            :value="`Peak ${settings.yMode} intensity: ${num.peakIntensity.format(settings.yMode == 'average' ? isotopeChart.sample_peak_intensity : isotopeChart.sample_peak_intensity * sampleLength)}`"
            :severity="
              isotopeChart.sample_peak_intensity < app.data.match.params.ui.peak_min_intensity
                ? 'warn'
                : 'info'
            "
          />
          <Tag
            :value="`m/z error (ppm): ${num.mzError.format(isotopeChart.match_mz_error)}`"
            :severity="
              Math.abs(isotopeChart.match_mz_error) > app.data.match.params.ui.mz_tolerance
                ? 'warn'
                : 'info'
            "
          />

          <Tag
            :value="`Abundance error: ${num.relativeAbundanceError.format(isotopeChart.match_abundance_error)}`"
            :severity="
              Math.abs(isotopeChart.match_abundance_error) >
              app.data.match.params.ui.isotope_ratio_tolerance
                ? 'warn'
                : 'info'
            "
          />
        </div>
      </figure>
    </div>
  </div>
</template>

<style scoped>
#chart-spectrum-controls :global(fieldset) {
  margin: 0 !important;
}

@layer override {
  .float {
    flex-flow: column nowrap;
    gap: 0.5rem;
    align-items: flex-end;
    position: absolute;
    top: 5rem;
    right: 1rem;
    display: none;
    :deep(*) {
      font-size: smaller;
    }
  }

  figure:hover .float,
  .sidebarOpen .float {
    display: flex;
  }
}
</style>
