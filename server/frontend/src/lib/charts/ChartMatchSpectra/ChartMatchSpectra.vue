<script setup>
import { ref, computed, toRaw } from 'vue'

import Tag from 'primevue/tag'

import { BaseMatchTag } from '@/lib/base'
import { clone } from '@/lib/utils'
import { num } from '@/lib/formatters'
import { useApp } from '@/stores'
import { ToolbarIntensityScale } from '@/lib/toolbars'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useChartData } from './data.js'

const app = useApp()
const data = useChartData()

const plots = ref({})

const props = defineProps({
  sidebarOpen: {
    type: Boolean,
    required: true
  },
  height: {
    type: Number,
    required: false
  }
})

const scale = defineModel()

const sampleLength = computed(() =>
  app.data.sample.selected.length != 1 ? null : app.data.sample.selected[0].length
)

const traces = computed(() => {
  // Scale trace y-values based on "average / sum" toggle
  if (sampleLength === null) {
    return []
  }
  return scale.value.mode == 'average'
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
  return clone(app.data.match.visualized.isotopes)?.map((isotope) => {
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
    return {
      // all match isotope fields
      ...isotope,
      // and our computed data
      traces: isotopeTraces
    }
  })
})

// compute match category with UI match params
const getIsotopeCategory = (isotope) => {
  if (!isotope?.match) return 0
  // This accesses app.data.match.params.ui inside the function,
  return app.data.match.params.uiCategory(isotope.match)
}

// auto vs manual scale
const rangeY = computed(
  () =>
    scale.value.max // if user set the scale
      ? { range: [0, scale.value.max], autorange: false } // use set scale
      : { range: null, autorange: true } // otherwise auto set scale
)
// standard plotly layout, a clone of this is used for each chart
const layout = computed(() => {
  return {
    yaxis: {
      title: {
        text: `Signal intensity [${scale.value.mode == 'average' ? 'counts/s' : 'counts'}]`
      },
      gridcolor: '#33333399',
      rangemode: 'nonnegative',
      type: scale.value.log ? 'log' : 'lin',
      ...rangeY.value
    },
    xaxis: {
      title: { text: 'm/z [Th]' },
      gridcolor: '#33333399',
      autorange: true
    },
    margin: { l: 50, r: 20, t: 40, b: 40 },
    dragmode: 'zoom',
    showlegend: false,
    height: props.height
  }
})
</script>

<template>
  <div class="spectra-container">
    <div class="row spectra-scroll">
      <figure
        v-for="(isotopeChart, index) of isotopeCharts"
        :key="`${isotopeChart.target_isotope_id}-${height}`"
        class="spectra-figure"
        :class="{ sidebarOpen }"
      >
        <h3 :style="`color: ${isotopeChart.traces[0]?.line.color}; margin: 0`">
          <BaseMatchTag
            :match-score="isotopeChart.match?.match_score"
            :match-category="getIsotopeCategory(isotopeChart)"
            :alarming="isotopeChart.match?.alarming"
          />
          {{ isotopeChart.target_isotope_formula }}: {{ num.mz.format(isotopeChart.mz) }}
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
          :title="`${isotopeChart.target_isotope_formula}: ${num.mz.format(isotopeChart.mz)}`"
          :ref="(el) => (plots[index] = el)"
          :data="isotopeChart.traces"
          :layout="clone(layout)"
          hideTitle
        >
          <template v-slot:settings>
            <ToolbarIntensityScale v-model="scale" />
          </template>
        </BaseChartPlotly>
        <div class="float">
          <Tag
            :value="`Peak ${scale.mode} intensity: ${num.peakIntensity.format(scale.mode == 'average' ? isotopeChart.match.sample_peak_intensity : isotopeChart.match.sample_peak_intensity * sampleLength)}`"
            :severity="
              isotopeChart.match.sample_peak_intensity < app.data.match.params.ui.peak_min_intensity
                ? 'warn'
                : 'info'
            "
          />
          <Tag
            :value="`m/z error (ppm): ${num.mzError.format(isotopeChart.match.match_mz_error)}`"
            :severity="
              Math.abs(isotopeChart.match.match_mz_error) > app.data.match.params.ui.mz_tolerance
                ? 'warn'
                : 'info'
            "
          />

          <Tag
            :value="`Abundance error: ${num.relativeAbundanceError.format(isotopeChart.match.match_abundance_error)}`"
            :severity="
              Math.abs(isotopeChart.match.match_abundance_error) >
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
.spectra-container {
  width: 100%;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.spectra-scroll {
  display: inline-flex;
  flex-flow: row nowrap;
  gap: 0;
  align-items: flex-start;
  justify-content: flex-start;
  min-width: 100%;
  padding: 0;
  margin: 0;
}

.spectra-figure {
  flex-shrink: 0;
  flex-grow: 1;
  min-width: 300px;
  position: relative;
}

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
