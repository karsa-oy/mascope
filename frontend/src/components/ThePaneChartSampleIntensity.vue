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
import BaseChartPlotly from "./BaseChartPlotly.vue";
import { get } from "vuex-pathify";
import { glasbeyHv } from "$lib/styles";

export default {
  name: "ThePaneChartSampleIntensity",
  components: { BaseChartPlotly },
  computed: {
    ...get({
      sampleItems: "batch/sampleItems",
      targetCompounds: "batch/targetCompounds",
      matchCompounds: "batch/matchCompounds",
    }),
    probable: function () {
      return this.stats.filter((stat) => stat.rating == "probable");
    },
    possible: function () {
      return this.stats.filter((stat) => stat.rating == "possible");
    },
    data: function () {
      if (!(this.sampleItems && this.matchCompounds)) return [];
      let allCompoundIds = this.targetCompounds.map(
        (compound) => compound.target_compound_id
      );
      let compoundColors = Object.fromEntries(
        allCompoundIds.map((compoundId, index) => [
          [compoundId],
          glasbeyHv[index],
        ])
      );
      let data = [];
      // Loop through sample items
      for (let item of this.sampleItems) {
        let x = [item.sample_item_id];
        let itemMatches = this.matchCompounds.filter(
          (row) => row.sample_item_id === item.sample_item_id
        );
        // Loop through target compounds
        for (let compound of this.targetCompounds) {
          let y = itemMatches
            .filter(
              (match) =>
                match.target_compound_id === compound.target_compound_id
            )
            .map((compoundMatch) => compoundMatch.sample_peak_area_sum);
          let compoundColor = compoundColors[compound.target_compound_id];
          let markerSymbol =
            compound.rating === "probable" ? "square" : "square-open";
          data.push({
            name: compound.target_compound_name.trim()
              ? compound.target_compound_name
              : compound.target_compound_formula,
            x,
            y,
            mode: "markers",
            type: "scatter",
            marker: {
              color: `rgb(${compoundColor[0]},${compoundColor[1]},${compoundColor[2]})`,
              size: 10,
              symbol: markerSymbol,
            },
          });
        }
      }
      return data;
    },
    layout: function () {
      return {
        xaxis: {
          title: "Sample item",
          autorange: true,
          showgrid: true,
          tickmode: "array",
          tickvals: this.sampleItems.map((item) => item.sample_item_id),
          ticktext: this.sampleItems.map((item) => item.sample_item_name),
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
    onClick: function (event) {
      console.log(event);
    },
  },
};
</script>
