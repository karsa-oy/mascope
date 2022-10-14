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
import BaseChartPlotly from "./BaseChartPlotly.vue";

import { get } from "vuex-pathify";

export default {
  name: "ThePaneChartSampleMatchCount",
  components: { BaseChartPlotly },
  computed: {
    ...get({
      sampleItems: "batch/sampleItems",
      targetCompounds: "batch/targetCompounds",
      matchCompounds: "batch/matchCompounds",
      possibleMatchThreshold: "batch/paramPossibleMatchThreshold",
      probableMatchThreshold: "batch/paramProbableMatchThreshold",
    }),
    data: function () {
      if (!(this.sampleItems && this.matchCompounds)) return [];
      return [
        {
          name: "Probable match",
          x: this.sampleItems.map((item) => item.sample_item_id),
          y: this.sampleItems.map((item) => this.itemMatchCompoundProbableCount(item.sample_item_id)),
          type: "bar",
          marker: {
            color: "#5cb85c",
          },
        },
        {
          name: "Possible match",
          x: this.sampleItems.map((item) => item.sample_item_id),
          y: this.sampleItems.map((item) => this.itemMatchCompoundPossibleCount(item.sample_item_id)),
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
          tickvals: this.sampleItems.map((item) => item.sample_item_id),
          ticktext: this.sampleItems.map((item) => item.sample_item_name),
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
    itemMatchCompoundPossibleCount: function(sampleItemId) {
      return this.matchCompounds
        .filter((item) => item.sample_item_id === sampleItemId)
        .filter((match) => 
          (match.match_score >= this.possibleMatchThreshol
          && match.match_score < this.probableMatchThreshold)
          )
        .length
    },
    itemMatchCompoundProbableCount: function(sampleItemId) {
      return this.matchCompounds
        .filter((item) => item.sample_item_id === sampleItemId)
        .filter((match) => match.match_score >= this.probableMatchThreshold)
        .length
    },
    onClick: function (event) {
      console.log(event);
    },
  },
};
</script>