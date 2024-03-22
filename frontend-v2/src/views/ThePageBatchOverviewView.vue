<script setup>
import TheLayoutSidebarView from './TheLayoutSidebarView.vue'

import ThePaneBrowser from '@/components/ThePaneBrowser.vue'
import ThePaneChartSampleIntensity from '@/components/ThePaneChartSampleIntensity.vue'
</script>

<template>
  <the-layout-sidebar-view>
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
  </the-layout-sidebar-view>
</template>
