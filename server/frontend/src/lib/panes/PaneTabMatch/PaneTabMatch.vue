<script setup>
import ScrollPanel from 'primevue/scrollpanel'

import { computed, ref, reactive } from 'vue'

import { BaseMatchTag } from '@/lib/base'
import { ChartMatchSpectra, ChartMatchTimeseries } from '@/lib/charts'
import { ToolbarMatchCharts, ToolbarMatchRating } from '@/lib/toolbars'
import { useApp } from '@/stores'

import SidebarMatchParams from './SidebarMatchParams.vue'

const app = useApp()

const compound = computed(() =>
  app.data.match.compound.list.find(
    ({ target_compound_id }) =>
      target_compound_id == app.data.match.visualized.ion?.target_compound_id
  )
)

const settings = reactive({
  intensityScale: null,
  yMode: 'sum'
})

// recompute match category with the UI's param state
const uiScoredIon = computed(() => {
  const ion = app.data.match.visualized.ion
  return {
    ...ion,
    match_category: app.data.match.params.uiCategory(ion)
  }
})

const sidebarOpen = ref(false)
</script>

<template>
  <div
    :style="`
      height: calc(100vh - 150px); 
      width: calc(${app.ui.split.right}vw - 5rem);
      overflow-y: auto;
      overflow-x: hidden;
    `"
    v-if="app.data.match.params.ui"
  >
    <menu class="topbar">
      <div>
        <SidebarMatchParams v-model:open="sidebarOpen" />
      </div>
      <h1>
        <BaseMatchTag :row="uiScoredIon" :style="'font-size: large'" />
        match: ion <i>{{ app.data.match.visualized.ion?.target_ion_formula }}</i>
        for
        <i>{{ app.data.match.visualized.ion?.sample_item_name }}</i> with target
        <i>{{ compound?.target_compound_formula }}</i>
      </h1>
      <div class="row">
        <ToolbarMatchCharts
          v-model:scale="settings.intensityScale"
          v-model:yMode="settings.yMode"
        />
        <ToolbarMatchRating />
      </div>
    </menu>
    <ChartMatchSpectra :settings="settings" :sidebarOpen="sidebarOpen" />
    <ChartMatchTimeseries :settings="settings" />
  </div>
</template>

<style scoped>
.topbar {
  width: 100%;
  display: flex;
  flex-flow: row nowrap;
  justify-content: space-between;
  align-items: flex-start;
  margin: 0;
  padding: 0;
  gap: 1rem;
  margin-bottom: 1rem;

  h1 {
    margin: 0;
    padding: 0;
    padding-top: 0.5rem;
  }
}
</style>
