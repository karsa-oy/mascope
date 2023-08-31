<template>
  <base-chart-plotly
    id="ChartSampleIntensity"
    :title="this.batchActive.sample_batch_name"
    :data="data"
    :layout="layout"
    @click="onClick"
  ></base-chart-plotly>
</template>

<script>
import BaseChartPlotly from "./BaseChartPlotly.vue";
import { call, get } from "vuex-pathify";
import { glasbeyHv } from "$lib/styles";

export default {
  name: "ThePaneChartSampleIntensity",
  components: { BaseChartPlotly },
  computed: {
    ...get({
      batchActive: "batch/active",
      matchCompounds: "batch/matchCompounds",
      paramPossibleMatchThreshold: "batch/paramPossibleMatchThreshold",
      paramProbableMatchThreshold: "batch/paramProbableMatchThreshold",
      sampleItems: "batch/sampleItems",
      targetCompounds: "batch/targetCompounds",
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
      allCompoundIds = [...new Set(allCompoundIds)];
      let compoundColors = Object.fromEntries(
        allCompoundIds.map((compoundId, index) => [
          [compoundId],
          glasbeyHv[index],
        ])
      );
      let data = [];
      let x = this.sampleItems.map((item) => item.sample_item_id);

      // Loop through target compounds, make traces and push to data
      for (let targetCompoundId of allCompoundIds) {
        let y = [];
        let compoundMaxMatchScore = 0;
        for (let sampleItemId of x) {
          let itemMatches = this.matchCompounds.filter(
            (row) => row.sample_item_id === sampleItemId
          );
          let sampleItemCompoundStats = itemMatches
            .filter((match) => match.target_compound_id === targetCompoundId)
            .map((compoundMatch) =>
              Object.fromEntries([
                ["match_score", compoundMatch.match_score],
                ["intensity", compoundMatch.sample_peak_area_sum],
              ])
            )[0];
          if (!sampleItemCompoundStats) continue;
          let sampleItemCompoundMatchScore =
            sampleItemCompoundStats.match_score;
          let sampleItemCompoundIntensity = sampleItemCompoundStats.intensity;

          y.push(
            sampleItemCompoundMatchScore >= this.paramPossibleMatchThreshold
              ? sampleItemCompoundIntensity
              : null
          );
          compoundMaxMatchScore = Math.max(
            compoundMaxMatchScore,
            sampleItemCompoundMatchScore
          );
        }
        if (y.every((intensity) => intensity === null)) continue;
        let compoundSymbol =
          compoundMaxMatchScore >= this.paramProbableMatchThreshold
            ? "square"
            : "square-open";
        let compoundColor = compoundColors[targetCompoundId];
        let compound = this.targetCompounds.filter(
          (target) => target.target_compound_id === targetCompoundId
        )[0];
        data.push({
          name: compound.target_compound_name.trim()
            ? compound.target_compound_name
            : compound.target_compound_formula,
          target_compound_id: targetCompoundId,
          x,
          y,
          mode: "markers",
          type: "scatter",
          marker: {
            color: `rgb(${compoundColor[0]},${compoundColor[1]},${compoundColor[2]})`,
            size: 10,
            symbol: compoundSymbol,
          },
        });
      }
      // Make trace for TIC
      let y = this.sampleItems.map((item) => item.tic);
      data.push({
        name: "TIC",
        x,
        y,
        mode: "markers",
        type: "scatter",
        marker: {
          color: "white",
          size: 10,
          symbol: "diamond",
        },
      });

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
          gridcolor: "#464752",
          gridwidth: 1,
        },
        yaxis: {
          title: "Intensity",
          showgrid: true,
          autorange: true,
          rangemode: "tozero",
          gridcolor: "#464752",
          gridwidth: 1,
        },
        showlegend: true,
      };
    },
  },
  methods: {
    ...call({
      itemFocus: "batch/sampleItemFocus",
      itemToggle: "batch/sampleItemToggle",
    }),
    itemSelect(row) {
      this.itemToggle(row);
      this.itemFocus(row);
    },
    onClick: function (event) {
      // Select sample item corresponding to clicked data point
      let sampleItemIndex = event.points[0].pointIndex;
      let sampleItem = this.sampleItems[sampleItemIndex];
      this.itemSelect(sampleItem);
      // Mouse button dependent action
      switch (event.event.button) {
        case 0:
          // Left click
          break;
        case 1:
          // Middle click
          break;
        case 2:
          // Right click
          break;
      }
    },
  },
};
</script>
