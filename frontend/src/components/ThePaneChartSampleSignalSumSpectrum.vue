<template>
  <base-chart-plotly
    id="ChartSampleSignalSumSpectrum"
    title="Sum spectrum"
    :data="data"
    :layout="layout"
  ></base-chart-plotly>
</template>

<script>
import BaseChartPlotly from "./BaseChartPlotly.vue";

import { get } from "vuex-pathify";

export default {
  name: "ThePaneChartSampleSignalSumSpectrum",
  components: { BaseChartPlotly },
  computed: {
    ...get({
      sampleFocused: "sample/active",
      traces: "visualization/tracesSignalSumSpectrum",
      isotopesInFocus: "visualization/isotopesInFocus",
    }),
    data: function () {
      return this.traces ? this.traces : [];
    },
    layout: function () {
      const annotations = this.isotopesInFocus.map((isotope, index) => {
        if (isotope.sample_peak_area === 0) return null;

        const xPosition = index === 0 ? 0.22 : 0.77; // Adjust these values to position the titles correctly
        return {
          text: `Target isotope intensity: ${this.formatNumber(
            isotope.sample_peak_area.toFixed(0)
          )}`,
          font: {
            size: 14,
          },
          showarrow: false,
          align: "center",
          x: xPosition,
          xref: "paper",
          xanchor: "center",
          y: 1.12,
          yref: "paper",
        };
      });
      return {
        grid: {
          rows: 1,
          columns: 2,
          pattern: "independent",
        },
        yaxis: this.yAxisConfiguration,
        xaxis: this.xAxisConfiguration,
        yaxis2: this.yAxisConfiguration,
        xaxis2: this.xAxisConfiguration,
        dragmode: "zoom",
        showlegend: false,
        height: "400",
        width: "860",
        annotations: annotations,
      };
    },
    xAxisConfiguration() {
      return {
        title: "m/z [Th]",
        gridcolor: "#464752",
        gridwidth: 1,
      };
    },
    yAxisConfiguration() {
      return {
        title: "Signal intensity [cps]",
        gridcolor: "#464752",
        gridwidth: 1,
      };
    },
  },
  methods: {
    formatNumber(value) {
      const roundedValue = Math.round(value);
      const formatter = new Intl.NumberFormat("en-US");
      return formatter.format(roundedValue);
    },
  },
};
</script>
