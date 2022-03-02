<template>
  <base-chart-plotly
    id="ChartSampleIntensity"
    title="Match peak intensity by sample item"
    :data="data"
    :layout="layout"
    @click="onClick"
  ></base-chart-plotly>
</template>

<script>
import BaseChartPlotly from "./BaseChartPlotly";

import { mapActions } from "vuex";

export default {
  name: "ThePaneChartSampleIntensity",
  components: { BaseChartPlotly },
  computed: {
    stats: function () {
      return this.$store.getters["match/ratings"]({
        level: "compound",
        selected: true,
      });
    },
    probable: function () {
      return this.stats.filter((stat) => stat.rating == "probable");
    },
    possible: function () {
      return this.stats.filter((stat) => stat.rating == "possible");
    },
    data: function () {
      return [
        {
          name: "Probable match",
          x: this.probable.map((stat) => stat.sampleFilename),
          y: this.probable.map((stat) => stat.samplePeakHeight),
          id: this.probable.map((stat) => stat.sampleItemId),
          mode: "markers",
          type: "scatter",
          marker: {
            size: 10,
            color: "#5cb85c",
          },
        },
        {
          name: "Possible match",
          x: this.possible.map((stat) => stat.sampleFilename),
          y: this.possible.map((stat) => stat.samplePeakHeight),
          id: this.possible.map((stat) => stat.sampleItemId),
          mode: "markers",
          type: "scatter",
          marker: {
            size: 10,
            color: "#df691a",
          },
        },
      ];
    },
    layout: function () {
      return {
        xaxis: {
          title: "Sample item",
          autorange: true,
          showgrid: true,
          tickmode: "array",
          tickvals: this.stats.map((item, index) => index),
          ticktext: this.stats.map((item, index) => index + 1),
          gridcolor: "#757575",
        },
        yaxis: {
          title: "Peak intensity",
          showgrid: true,
          autorange: true,
          rangemode: "tozero",
          gridcolor: "#757575",
        },
        showlegend: false,
      };
    },
  },
  methods: {
    ...mapActions("sample", {
      toggleSampleItemSelection: "itemSelectionToggle",
    }),
    onClick: function (event) {
      console.log(event);
    },
  },
};
</script>