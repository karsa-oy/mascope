<template>
  <base-chart-plotly
    id="ChartSampleIntensity"
    title="Target compound intensity by sample item"
    :data="data"
    :layout="layout"
    @click="onClick"
  ></base-chart-plotly>
</template>

<script>
import BaseChartPlotly from "./BaseChartPlotly";
import { glasbeyHv } from "$lib/colorcet"
import { mapActions } from "vuex";

export default {
  name: "ThePaneChartSampleIntensity",
  components: { BaseChartPlotly },
  computed: {
    stats: function () {
      return this.$store.getters["match/rating/rows"]({
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
      if (!this.stats.length) return [];
      // Read target compound ids from the first sample item
      // and make an object with id as key and color as value 
      let allCompoundIds = this.stats.map((stat) => stat.targetCompoundId);
      let uniqueCompoundIds = [...new Set(allCompoundIds)];
      let compoundColors = Object.fromEntries(
        uniqueCompoundIds.map((compoundId, index) => 
          ([ [compoundId], glasbeyHv[index] ])
          )
      );
      let data = [];
      for (let stat of this.stats) {
        let compoundColor = compoundColors[stat.targetCompoundId];
        let markerSymbol = stat.rating ==='probable' ? 'square' : 'square-open';
        data.push({
          name: stat.targetName.trim() ? stat.targetName : stat.targetFormula,
          x: [stat.sampleItemId],
          y: [stat.samplePeakHeight],
          mode: "markers",
          type: "scatter",
          marker: {
            color: `rgb(${compoundColor[0]},${compoundColor[1]},${compoundColor[2]})`,
            size: 10,
            symbol: markerSymbol,
          },
        });
      }
      return data
    },
    layout: function () {
      return {
        xaxis: {
          title: "Sample item",
          autorange: true,
          showgrid: true,
          tickmode: "array",
          tickvals: this.stats.map((item) => item.sampleItemId),
          ticktext: this.stats.map((item) => item.sampleTitle),
          gridcolor: "#757575",
        },
        yaxis: {
          title: "Intensity",
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