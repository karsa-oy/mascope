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
      return this.$store.getters["sample/item/stat/rows"]({
        level: "compound",
        selected: true,
      });
    },
    data: function () {
      return [
        {
          name: "Probable match",
          x: this.stats.map((stat) => stat.id),
          y: this.stats.map((stat) => stat.matchCompoundProbableCount),
          type: "bar",
          marker: {
            color: "#5cb85c",
          },
        },
        {
          name: "Possible match",
          x: this.stats.map((stat) => stat.id),
          y: this.stats.map((stat) => stat.matchCompoundPossibleCount),
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
          tickvals: this.stats.map((item) => item.id),
          ticktext: this.stats.map((item) => item.title),
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
    ...mapActions("sample", {
      toggleSampleItemSelection: "itemSelectionToggle",
    }),
    onClick: function (event) {
      console.log(event);
    },
  },
};
</script>