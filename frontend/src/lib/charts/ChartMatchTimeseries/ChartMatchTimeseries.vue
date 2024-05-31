<script setup>
import { computed } from 'vue'
import Tag from 'primevue/tag'

import BaseChartPlotly from '../BaseChartPlotly.vue'

import { useData } from './data'

import { useFocusedMatch, useFilterParams } from '@/stores'

const focusedMatch = useFocusedMatch()
const filterParams = useFilterParams()

const data = useData()

const layout = computed(() => ({
  xaxis: {
    title: 'Time [s]',
    autorange: true,
    showgrid: true,
    gridcolor: '#33333399',
    gridwidth: 1
  },
  yaxis: {
    title: 'Peak height [cps]',
    showgrid: true,
    autorange: true,
    rangemode: 'tozero',
    gridcolor: '#33333399',
    gridwidth: 1
  },
  dragmode: 'zoom',
  showlegend: true
}))

const corr = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})
</script>

<template>
  <figure>
    <span>
      isotope correlation coefficient:
      <Tag
        :value="corr.format(focusedMatch.isotopes[0].match_isotope_correlation)"
        :severity="
          Math.abs(focusedMatch.isotopes[0].match_isotope_correlation) >
          filterParams.min_isotope_correlation
            ? 'info'
            : 'warn'
        "
      />
    </span>
    <BaseChartPlotly
      id="ChartMatchTimeseries"
      title="Timeseries"
      :data="data.traces"
      :layout="layout"
    />
  </figure>
</template>
