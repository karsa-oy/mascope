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
import BaseChartPlotly from "./BaseChartPlotly.vue";

import { mapActions } from "vuex";

let barSum = (row) =>
  row.matchCompoundProbableCount + row.matchCompoundPossibleCount;

let compareMatches = (rowA, rowB) =>
  rowB.matchCompoundProbableCount - rowA.matchCompoundProbableCount ||
  rowB.matchCompoundPossibleCount - rowA.matchCompoundPossibleCount;

export default {
  name: "ThePaneChartTargetMatchCount",
  components: { BaseChartPlotly },
  computed: {
    stats: function () {
      return this.$store.getters["target/stat/rows"]({
        level: "compound",
        selected: true,
      })
        .filter((row) => barSum(row) > 0)
        .sort(compareMatches);
    },
    data: function () {
      return [
        {
          name: "Probable matches",
          x: this.stats.map((row) => row.id),
          y: this.stats.map((row) => row.matchCompoundProbableCount),
          type: "bar",
          marker: {
            color: "#5cb85c",
          },
        },
        {
          name: "Possible matches",
          x: this.stats.map((row) => row.id),
          y: this.stats.map((row) => row.matchCompoundPossibleCount),
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
          tickvals: this.stats.map((stat) => stat.id),
          ticktext: this.stats.map((stat) =>
            stat.target_compound_name.trim() ? stat.target_compound_name : stat.target_compound_formula
          ),
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
    ...mapActions("sample", {
      toggleSampleItemSelection: "itemSelectionToggle",
    }),
    onClick: function (event) {
      console.log(event);
    },
  },
};
</script>