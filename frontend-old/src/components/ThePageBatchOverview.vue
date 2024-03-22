<template>
  <the-layout-sidebar>
    <section>
      <div class="columns" style="margin: 0 auto; width: 80vw">
        <div class="column is-7">
          <the-pane-chart-sample-intensity></the-pane-chart-sample-intensity>
        </div>
        <div class="column is-5">
          <the-pane-browser></the-pane-browser>
        </div>
      </div>
    </section>
  </the-layout-sidebar>
</template>

<script>
import TheLayoutSidebar from './TheLayoutSidebar.vue'
import ThePaneBrowser from './ThePaneBrowser.vue'
import ThePaneChartSampleIntensity from './ThePaneChartSampleIntensity.vue'

export default {
  name: 'ThePageBatchOverview',
  components: {
    TheLayoutSidebar,
    ThePaneBrowser,
    ThePaneChartSampleIntensity,
  },
}
</script>
