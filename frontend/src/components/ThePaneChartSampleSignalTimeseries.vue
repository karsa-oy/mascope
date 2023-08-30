<template>
  <base-chart-plotly
    id="ChartSampleSignalTimeseries"
    title="Timeseries"
    :data="data"
    :layout="layout"
  ></base-chart-plotly>
</template>

<script>
import BaseChartPlotly from "./BaseChartPlotly.vue";

import { get } from "vuex-pathify";

export default {
  name: "ThePaneChartSampleSignalTimeseries",
  components: { BaseChartPlotly },
  computed: {
    ...get({
      sampleFocused: "sample/active",
      traces: "visualization/tracesSignalTimeseries",
    }),
    data: function () {
      return this.traces ? this.traces : [];
    },
    layout: function () {
      return {
        xaxis: {
          title: "Time [s]",
          autorange: true,
          showgrid: true,
          gridcolor: "black",
          gridwidth: 1,
        },
        yaxis: {
          title: "Peak height [cps]",
          showgrid: true,
          autorange: true,
          rangemode: "tozero",
          gridcolor: "black",
          gridwidth: 1,
        },
        dragmode: "zoom",
        showlegend: true,
        height: "400",
        width: "860",
      };
    },
  },
  methods: {},
};
</script>
