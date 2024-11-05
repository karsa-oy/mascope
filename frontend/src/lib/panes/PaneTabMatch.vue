<script setup>
import ScrollPanel from 'primevue/scrollpanel'

import { computed, reactive } from 'vue'

import { BaseMatchTag } from '@/lib/base'
import { ChartMatchSpectra, ChartMatchTimeseries } from '@/lib/charts'
import { ToolbarFilterIon, ToolbarMatchCharts, ToolbarMatchRating } from '@/lib/toolbars'
import { useApp } from '@/stores'

const app = useApp()

const compound = computed(() =>
  app.data.match.compound.list.find(
    ({ target_compound_id }) => target_compound_id == app.data.match.visualized.ion?.target_compound_id
  )
)

const settings = reactive({
  intensityScale: null
})
</script>

<template>
  <div
    :style="`
      height: calc(100vh - 150px); 
      width: calc(${app.ui.split.right}vw - 4rem);
    `"
  >
    <ScrollPanel style="height: calc(100vh - 150px); width: calc(100%-4rem)">
      <h1 style="text-align: center">
        <BaseMatchTag :row="app.data.match.visualized.ion" :style="'font-size: large'" />
        match: ion <i>{{ app.data.match.visualized.ion?.target_ion_formula }}</i>
        for
        <i>{{ app.data.match.visualized.ion?.sample_item_name }}</i> with target
        <i>{{ compound?.target_compound_formula }}</i>
      </h1>
      <ChartMatchSpectra :settings="settings" />
      <ChartMatchTimeseries />
      <div class="row match-tools">
        <ToolbarFilterIon />
        <ToolbarMatchCharts v-model:scale="settings.intensityScale" />
        <ToolbarMatchRating />
      </div>
    </ScrollPanel>
  </div>
</template>

<style scoped>
.match-tools {
  position: fixed;
  top: 72px;
  right: 7px;
  z-index: 50;
  justify-content: flex-end;
  padding: 0.5rem;
  border-radius: 0.5rem;
}

.match-tools :deep(*) {
  margin: 0;
}
</style>
