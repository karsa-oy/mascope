<template>
  <base-chart-plotly
    id="ChartTargetIntensity"
    title="Match count by target compound"
    :data="data"
    :layout="layout"
    @click="onClick"
  ></base-chart-plotly>
</template>

<script>
import BaseChartPlotly from "./BaseChartPlotly";

import { mapActions } from "vuex";

export default {
  name: "ThePaneChartTargetMatchCount",
  components: { BaseChartPlotly },
  computed: {
    stats: function () {
      return this.$store.getters["workspace/target/stats"]({
        level: "compound",
        selected: true,
        extraGroupings: ", m.rating",
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
          name: "Probable matches",
          x: this.probable.map((row) => row.formula),
          y: this.probable.map((row) => row.matchCount),
          id: this.probable.map((row) => row.id),
          type: "bar",
          marker: {
            color: "#5cb85c",
          },
        },
        {
          name: "Possible matches",
          x: this.possible.map((row) => row.formula),
          y: this.possible.map((row) => row.matchCount),
          id: this.possible.map((row) => row.id),
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
          title: "Target compound",
          autorange: true,
          showgrid: true,
          tickmode: "array",
          tickvals: this.stats.map((item, index) => index),
          ticktext: this.stats.map((stat) => stat.formula),
          gridcolor: "#757575",
        },
        yaxis: {
          title: "Match count",
          showgrid: true,
          autorange: true,
          rangemode: "tozero",
          gridcolor: "#757575",
          dtick: 1,
        },
        barmode: "stack",
        showlegend: false,
      };
    },
  },
  methods: {
    ...mapActions("workspace/sample", {
      toggleSampleItemSelection: "itemToggleSelection",
    }),
    onClick: function (event) {
      console.log(event);
    },
  },
};
</script>