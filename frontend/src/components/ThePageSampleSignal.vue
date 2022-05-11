<template>
  <the-layout-sidebar>
    <section>
      <div class="columns">
        <div class="column is-3 base-browser-sidebar">
          <the-pane-browser-target></the-pane-browser-target>
          <the-pane-browser-sample></the-pane-browser-sample>
        </div>
        <div class="column is-9">
          <the-pane-chart-sample-signal-sum-spectrum></the-pane-chart-sample-signal-sum-spectrum>
          <the-pane-chart-sample-signal-timeseries></the-pane-chart-sample-signal-timeseries>
        </div>
      </div>
    </section>
  </the-layout-sidebar>
</template>

<script>

import TheLayoutSidebar from "./TheLayoutSidebar";
import ThePaneBrowserSample from "./ThePaneBrowserSample";
import ThePaneBrowserTarget from "./ThePaneBrowserTarget";
import ThePaneChartSampleSignalSumSpectrum from "./ThePaneChartSampleSignalSumSpectrum";
import ThePaneChartSampleSignalTimeseries from './ThePaneChartSampleSignalTimeseries.vue';

export default {
  name: "ThePageSampleSignal",
  components: {
    TheLayoutSidebar,
    ThePaneBrowserTarget,
    ThePaneBrowserSample,
    ThePaneChartSampleSignalSumSpectrum,
    ThePaneChartSampleSignalTimeseries,
  }
};
</script>