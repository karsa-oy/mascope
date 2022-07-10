<template>
  <base-chart-plotly
    id="ChartMatchTotalCount"
    title="Total match count by match rating"
    :data="data"
    :layout="layout"
    @click="onClick"
  ></base-chart-plotly>
</template>

<script>
import BaseChartPlotly from "./BaseChartPlotly.vue";

import { ratingColors } from "$lib/styles";

import { mapActions } from "vuex";

export default {
  name: "ThePaneChartSampleMatchCount",
  components: { BaseChartPlotly },
  computed: {
    stats: function () {
      return this.$store.getters["match/stat/rows"]({
        level: "compound",
      });
    },
    data: function () {
      return [
        {
          name: "Match counts",
          labels: this.stats.map((stat) => stat.rating),
          values: this.stats.map((stat) => stat.matchCount),
          type: "pie",
          hole: 40,
          marker: {
            colors: this.stats
              .map((stat) => stat.rating)
              .map((rating) => ratingColors[rating]),
          },
        },
      ];
    },
    layout: function () {
      return {
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