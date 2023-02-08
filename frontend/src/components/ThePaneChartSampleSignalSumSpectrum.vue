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
          rows: 1,
          columns: 2,
          pattern: "independent",
        },
        yaxis: this.yAxisConfiguration,
        xaxis: this.xAxisConfiguration,
        yaxis2: this.yAxisConfiguration,
        xaxis2: this.xAxisConfiguration,
        dragmode: "zoom",
        showlegend: false,
        height: "400",
        width: "860",
      };
    },
    xAxisConfiguration() {
      return {
        title: 'm/z [Th]',
        gridcolor: "#757575",
      }
    },
    yAxisConfiguration() {
      return {
        title: 'Signal intensity [cps]',
        gridcolor: "#757575",
      }
    },
  },
};
</script>