<template>
  <base-chart-plotly
    id="ChartSampleSignalSumSpectrum"
    title="Sum spectrum"
    :data="data"
    :layout="layout"
  ></base-chart-plotly>
</template>

<script>
import { bindState } from "$lib/store";

import BaseChartPlotly from "./BaseChartPlotly.vue";

export default {
  name: "ThePaneChartSampleSignalSumSpectrum",
  components: { BaseChartPlotly },
  computed: {
    ...bindState({
      tracesSpectrum: "visualization/tracesSpectrum",
    }),
    data: function () {
      return this.tracesSpectrum;
    },
    layout: function () {
      return {
        grid: {
          rows: 3,
          columns: 3,
          pattern: "independent",
        },
        dragmode: "zoom",
        showlegend: false,
      };
    },
  },
};
</script>