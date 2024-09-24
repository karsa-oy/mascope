<script setup>
import { ref, computed, watchEffect } from 'vue'

import ScrollPanel from 'primevue/scrollpanel'
import Tag from 'primevue/tag'

import BaseChartPlotly from '../BaseChartPlotly.vue'

import { BaseMatchTag } from '@/lib/base'
import { clone } from '@/lib/utils'
import { useApp } from '@/stores'

import { useChartData } from './data.js'

const app = useApp()

const plots = ref({})

const props = defineProps({
  settings: {
    type: Object,
    required: true
  }
})

const isotopes = computed(() => {
  const data = useChartData()
  return clone(app.ui.matchVisualized.isotopes).map((isotope) => {
    const start = data.traces?.findIndex(
      (trace) => trace.target_isotope_id === isotope.target_isotope_id
    )
    const nextStart = data.traces?.findIndex(
      ({ target_isotope_id }, index) => target_isotope_id && index > start
    )
    const end = nextStart !== -1 ? nextStart : data.traces?.length
    const traces = data.traces?.slice(start, end)

    let match_category = 0
    if (isotope.match_score > app.data.filterParams.current.possible_match_threshold) {
      match_category = 1
    }
    if (isotope.match_score > app.data.filterParams.current.probable_match_threshold) {
      match_category = 2
    }

    return {
      ...isotope,
      traces,
      match_category
    }
  })
})

const layout = computed(() => ({
  yaxis: {
    title: 'Signal intensity [cps]',
    gridcolor: '#33333399',
    rangemode: 'nonnegative',
    ...(props.settings.intensityScale ? { range: [0, props.settings.intensityScale] } : {})
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

watchEffect(() => {
  isotopes.value.forEach(({ target_isotope_id }) => {
    console.log(target_isotope_id)
    const plot = plots.value[target_isotope_id]
    if (plot) {
      plot.resetZoom()
    }
  })
})
</script>

<template>
  <div>
    <ScrollPanel>
      <div class="row" style="gap: 1rem; justify-content: flex-start; padding: 0 2rem">
        <figure v-for="isotope of isotopes" :key="isotope.target_isotope_id">
          <h3 :style="`color: ${isotope.traces[0]?.line.color}; margin: 0`">
            Isotope {{ error.format(isotope.mz) }}
          </h3>
          <BaseChartPlotly
            :id="`ChartMatchSpectrum-${isotope.target_isotope_id}`"
            :title="`Isotope ${error.format(isotope.mz)}`"
            :ref="(el) => (plots[isotope.target_isotope_id] = el)"
            :data="isotope.traces"
            :layout="layout"
            hideTitle
          />
          <div
            id="chart-spectrum-controls"
            class="row"
            style="flex-wrap: wrap; max-width: 35ch; justify-content: center"
          >
            <BaseMatchTag :row="isotope" text />
            <Tag
              :value="`Intensity: ${area.format(isotope.sample_peak_area)}`"
              :severity="
                isotope.sample_peak_area < app.data.filterParams.current.peak_min_intensity
                  ? 'warn'
                  : 'info'
              "
            />
            <Tag
              :value="`mz error: ${error.format(isotope.match_mz_error)}`"
              :severity="
                Math.abs(isotope.match_mz_error) > app.data.filterParams.current.mz_tolerance
                  ? 'warn'
                  : 'info'
              "
            />

            <Tag
              :value="`Abundance error: ${error.format(isotope.match_abundance_error)}`"
              :severity="
                Math.abs(isotope.match_abundance_error) >
                app.data.filterParams.current.isotope_ratio_tolerance
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
