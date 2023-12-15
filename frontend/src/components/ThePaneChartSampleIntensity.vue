<template>
  <div class="columns">
    <div class="column is-1">
      <br /><br /><br />
      <b-field>
        <template #label
          ><div style="text-align: center">
            <b-icon icon="math-log"></b-icon></div
        ></template>
        <b-switch v-model="yAxisLog"></b-switch>
      </b-field>
    </div>
    <div class="column is-11">
      <base-chart-plotly
        id="ChartSampleIntensity"
        :title="this.batchActive ? this.batchActive.sample_batch_name : ''"
        :data="data"
        :layout="layout"
        @click="onClick"
      ></base-chart-plotly>
    </div>
  </div>
</template>

<script>
import BaseChartPlotly from "./BaseChartPlotly.vue";
import { call, get } from "vuex-pathify";
import { glasbeyLight } from "$lib/styles";

export default {
  name: "ThePaneChartSampleIntensity",
  components: { BaseChartPlotly },
  data: function () {
    return {
      hovertemplate:
        "<b># %{x}</b>" +
        "<br>" +
        "<b>%{text}</b>" +
        "<br>" +
        "y: %{y:,.0f}" +
        "<br>" +
        "%{customdata}",
      yAxisLog: false,
    };
  },
  computed: {
    ...get({
      batchActive: "batch/active",
      matchCompounds: "batch/matchCompounds",
      sampleItems: "batch/sampleItems",
      targetCompounds: "batch/targetCompounds",
    }),
    data: function () {
      if (!(this.sampleItems && this.matchCompounds)) return [];
      let allCompoundIds = this.targetCompounds.map(
        (compound) => compound.target_compound_id
      );
      allCompoundIds = [...new Set(allCompoundIds)];
      let compoundColors = Object.fromEntries(
        allCompoundIds.map((compoundId, index) => [
          [compoundId],
          glasbeyLight[index],
        ])
      );
      let data = [];
      let x = this.sampleItems.map((item) => item.sample_item_id);

      // Loop through target compounds, make traces and push to data
      for (let targetCompoundId of allCompoundIds) {
        let y = [];
        let compoundMaxMatchCategory;
        for (let sampleItemId of x) {
          let itemMatches = this.matchCompounds.filter(
            (row) => row.sample_item_id === sampleItemId
          );
          let sampleItemCompoundStats = itemMatches
            .filter((match) => match.target_compound_id === targetCompoundId)
            .map((compoundMatch) =>
              Object.fromEntries([
                ["match_category", compoundMatch.match_category],
                ["intensity", compoundMatch.sample_peak_area_sum],
              ])
            )[0];
          if (sampleItemCompoundStats) {
            y.push(
              sampleItemCompoundStats.match_category > 0
                ? sampleItemCompoundStats.intensity
                : null
            );
          } else {
            y.push(null);
          }
          compoundMaxMatchCategory =
            sampleItemCompoundStats?.match_category || 0;
        }
        if (y.every((intensity) => intensity === null)) continue;
        let compoundSymbol =
          compoundMaxMatchCategory === 2 ? "square" : "square-open";
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
          customdata: this.sampleItems.map((item) => item.datetime),
          text: this.sampleItems.map((item) => item.sample_item_name),
          hovertemplate: this.hovertemplate,
          mode: "markers",
          type: "scatter",
          marker: {
            color: compoundColor, //`rgb(${compoundColor[0]},${compoundColor[1]},${compoundColor[2]})`,
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
        customdata: this.sampleItems.map((item) => item.datetime),
        text: this.sampleItems.map((item) => item.sample_item_name),
        hovertemplate: this.hovertemplate,
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
          ticktext: this.sampleItems.map((_, i) => i + 1),
          gridcolor: "#464752",
          gridwidth: 1,
        },
        yaxis: {
          title: "Intensity",
          type: this.yAxisLog ? "log" : "lin",
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
