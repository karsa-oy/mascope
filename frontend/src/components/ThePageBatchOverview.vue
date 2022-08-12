<template>
  <the-layout-sidebar>
    <section>
      <div class="columns">
        <div class="column is-3 base-browser-sidebar">
          <the-pane-browser-target></the-pane-browser-target>
          <the-pane-browser-sample></the-pane-browser-sample>
        </div>
        <div class="column is-9">
          <div class="columns">
            <div class="column is-6">
              <the-pane-chart-sample-intensity></the-pane-chart-sample-intensity>
              <the-pane-chart-target-match-count></the-pane-chart-target-match-count>
            </div>
            <div class="column is-6">
              <the-pane-chart-match-total-count></the-pane-chart-match-total-count>
              <the-pane-chart-sample-match-count></the-pane-chart-sample-match-count>
            </div>
          </div>
        </div>
      </div>
    </section>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from "./TheLayoutSidebar.vue";
import ThePaneBrowserSample from "./ThePaneBrowserSample.vue";
import ThePaneBrowserTarget from "./ThePaneBrowserTarget.vue";
import ThePaneChartTargetMatchCount from "./ThePaneChartTargetMatchCount.vue";
import ThePaneChartSampleMatchCount from "./ThePaneChartSampleMatchCount.vue";
import ThePaneChartSampleIntensity from "./ThePaneChartSampleIntensity.vue";
import ThePaneChartMatchTotalCount from "./ThePaneChartMatchTotalCount.vue";

export default {
  name: "ThePageBatchOverview",
  components: {
    TheLayoutSidebar,
    ThePaneBrowserTarget,
    ThePaneBrowserSample,
    ThePaneChartTargetMatchCount,
    ThePaneChartSampleMatchCount,
    ThePaneChartSampleIntensity,
    ThePaneChartMatchTotalCount,
  },
};
</script>

<style>
.base-browser-sidebar {
  display: flex !important;
  flex-direction: column !important;
  max-height: 100vh !important;
  min-height: 100px;
}

.tabs {
  margin-bottom: 0px !important;
}
</style>