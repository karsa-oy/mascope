<script setup>
import { computed } from 'vue'

import ScrollPanel from 'primevue/scrollpanel'
import Tag from 'primevue/tag'

import BaseChartPlotly from '../BaseChartPlotly.vue'

import { clone } from '@/lib/utils'
import { useFocusedMatch, useFilterParams } from '@/stores'

import { useData } from './data'

const filterParams = useFilterParams()

const props = defineProps({
  settings: {
    type: Object,
    required: true
  }
})

const isotopes = computed(() => {
  const focusedMatch = useFocusedMatch()
  const data = useData()
  return clone(focusedMatch.isotopes).map((isotope) => {
    const start = data.traces?.findIndex(
      (trace) => trace.target_isotope_id === isotope.target_isotope_id
    )
    const nextStart = data.traces?.findIndex(
      ({ target_isotope_id }, index) => target_isotope_id && index > start
    )
    const end = nextStart !== -1 ? nextStart : data.traces?.length
    const traces = data.traces?.slice(start, end)

    return {
      ...isotope,
      traces
    }
  })
})

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
            :id="`ChartMatchSpectrum-${isotope.target_isotope_id}`"
            :title="`Target isotope intensity: ${area.format(isotope.sample_peak_area)}`"
            :data="isotope.traces"
            :layout="layout"
          />
          <span>
            mz error:
            <Tag
              :value="error.format(isotope.match_mz_error)"
              :severity="
                Math.abs(isotope.match_mz_error) > filterParams.current.mz_tolerance
                  ? 'warn'
                  : 'info'
              "
            />
            • abundance error:
            <Tag
              :value="error.format(isotope.match_abundance_error)"
              :severity="
                Math.abs(isotope.match_abundance_error) >
                filterParams.current.isotope_ratio_tolerance
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
