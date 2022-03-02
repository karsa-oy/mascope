<template>
  <base-chart-plotly
    id="ChartSampleMatchCount"
    title="Match count by sample item"
    :data="data"
    :layout="layout"
    @click="onClick"
  ></base-chart-plotly>
</template>

<script>
import BaseChartPlotly from "./BaseChartPlotly";

import { mapActions } from "vuex";

export default {
  name: "ThePaneChartSampleMatchCount",
  components: { BaseChartPlotly },
  computed: {
    stats: function () {
      return this.$store.getters["workspace/sample/itemStats"]({
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
          x: this.probable.map((stat) => stat.filename),
          y: this.probable.map((stat) => stat.matchCount),
          id: this.probable.map((stat) => stat.id),
          type: "bar",
          marker: {
            color: "#5cb85c",
          },
        },
        {
          name: "Possible match",
          x: this.possible.map((stat) => stat.filename),
          y: this.possible.map((stat) => stat.matchCount),
          id: this.possible.map((stat) => stat.id),
          type: "bar",
          marker: {
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
          title: "Match count",
          showgrid: true,
          autorange: true,
          rangemode: "tozero",
          gridcolor: "#757575",
        },
        showlegend: false,
        barmode: "stack",
      };
    },
  },
  methods: {
    ...mapActions("workspace/sample", {
      toggleSampleItemSelection: "itemSelectionToggle",
    }),
    onClick: function (event) {
      console.log(event);
    },
  },
};
</script>