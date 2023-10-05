<template>
  <section>
    <the-pane-chart-sample-signal-sum-spectrum></the-pane-chart-sample-signal-sum-spectrum>
    <the-pane-chart-sample-signal-timeseries></the-pane-chart-sample-signal-timeseries>
  </section>
</template>

<script>
import ThePaneChartSampleSignalSumSpectrum from "./ThePaneChartSampleSignalSumSpectrum.vue";
import ThePaneChartSampleSignalTimeseries from "./ThePaneChartSampleSignalTimeseries.vue";

export default {
  name: "ThePaneSampleSignal",
  components: {
    ThePaneChartSampleSignalSumSpectrum,
    ThePaneChartSampleSignalTimeseries,
  },
};
</script>
