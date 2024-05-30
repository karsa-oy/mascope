<script setup>
import { computed } from 'vue'

import ScrollPanel from 'primevue/scrollpanel'
import Tag from 'primevue/tag'

import BaseChartPlotly from './BaseChartPlotly.vue'

import { useVisualizationStore } from '@/stores'
import { clone } from '../utils'

const visualizationStore = useVisualizationStore()

const props = defineProps({
  settings: {
    type: Object,
    required: true
  }
})

const isotopes = computed(() =>
  clone(visualizationStore.activeIsotopes).map((isotope) => {
    const start = visualizationStore.tracesSignalSumSpectrum?.findIndex(
      (trace) => trace.target_isotope_id === isotope.target_isotope_id
    )
    const nextStart = visualizationStore.tracesSignalSumSpectrum?.findIndex(
      ({ target_isotope_id }, index) => target_isotope_id && index > start
    )
    const end = nextStart !== -1 ? nextStart : visualizationStore.tracesSignalSumSpectrum?.length
    const traces = visualizationStore.tracesSignalSumSpectrum?.slice(start, end)

    return {
      ...isotope,
      traces
    }
  })
)

const layout = computed(() => ({
  yaxis: {
    title: 'Signal intensity [cps]',
    gridcolor: '#33333399',
    ...(props.settings.intensityScale ? { range: [0, props.settings.intensityScale] } : {})
  },
  xaxis: {
    title: 'm/z [Th]',
    gridcolor: '#33333399'
  },
  dragmode: 'zoom',
  showlegend: false,
  height: '350',
  width: '400'
}))

const area = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 0
})
const error = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})
</script>

<template>
  <div>
    <ScrollPanel>
      <div class="row" style="gap: 1rem; justify-content: flex-start; padding: 0 2rem">
        <figure v-for="isotope of isotopes" :key="isotope.target_isotope_id">
          <BaseChartPlotly
            :id="`ChartSampleSignalSumSpectrum-${isotope.target_isotope_id}`"
            :title="`Target isotope intensity: ${area.format(isotope.sample_peak_area)}`"
            :data="isotope.traces"
            :layout="layout"
          />
          <span>
            mz error:
            <Tag
              :value="error.format(isotope.match_mz_error)"
              :severity="
                Math.abs(isotope.match_mz_error) > visualizationStore.paramMzTolerance
                  ? 'warn'
                  : 'info'
              "
            />
            • abundance error:
            <Tag
              :value="error.format(isotope.match_abundance_error)"
              :severity="
                Math.abs(isotope.match_abundance_error) >
                visualizationStore.paramIsotopeRatioTolerance
                  ? 'warn'
                  : 'info'
              "
            />
          </span>
        </figure>
      </div>
    </ScrollPanel>
  </div>
</template>
