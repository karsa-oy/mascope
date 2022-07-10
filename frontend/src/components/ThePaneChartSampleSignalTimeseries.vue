<template>
  <base-chart-plotly
    id="ChartSampleSignalTimeseries"
    title="Timeseries"
    :data="data"
    :layout="layout"
  ></base-chart-plotly>
</template>

<script>
import { bindState } from "$lib/store";

import BaseChartPlotly from "./BaseChartPlotly.vue";

export default {
  name: "ThePaneChartSampleSignalTimeseries",
  components: { BaseChartPlotly },
  computed: {
    ...bindState({
      tracesProfile: "visualization/tracesProfile",
    }),
    data: function () {
      return this.tracesProfile;
    },
    layout: function () {
      return {
        xaxis: {
          title: "Time [s]",
          autorange: true,
          showgrid: true,
          gridcolor: "#757575",
        },
        yaxis: {
          title: "Integrated signal [a.u.]",
          showgrid: true,
          autorange: true,
          rangemode: "tozero",
          gridcolor: "#757575",
        },
        dragmode: "zoom",
        showlegend: true,
      };
    },
  },
  methods: {},
};
</script>