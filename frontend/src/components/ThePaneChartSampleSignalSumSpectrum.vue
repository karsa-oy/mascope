<template>
  <base-chart-plotly
    id="ChartSampleSignalSumSpectrum"
    title="Sum spectrum"
    :data="data"
    :layout="layout"
  ></base-chart-plotly>
</template>

<script>
import BaseChartPlotly from "./BaseChartPlotly.vue";

import { get } from "vuex-pathify";

export default {
  name: "ThePaneChartSampleSignalSumSpectrum",
  components: { BaseChartPlotly },
  computed: {
    ...get({
      sampleFocused: "sample/active",
      traces: "visualization/tracesSignalSumSpectrum",
    }),
    data: function () {
      return this.traces
        ? this.traces
        : [];
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