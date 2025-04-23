<script setup>
import { computed, ref, reactive } from 'vue'

import ScrollPanel from 'primevue/scrollpanel'
import Splitter from 'primevue/splitter'
import SplitterPanel from 'primevue/splitterpanel'

import { useWindowSize } from '@vueuse/core'

import { BaseMatchTag } from '@/lib/base'
import { ChartMatchSpectra, ChartMatchTimeseries } from '@/lib/charts'
import { ToolbarMatchCharts, ToolbarMatchRating } from '@/lib/toolbars'
import { useApp } from '@/stores'

import SidebarMatchParams from './SidebarMatchParams.vue'

const { height } = useWindowSize()

const app = useApp()

const compound = computed(() =>
  app.data.match.compound.list.find(
    ({ target_compound_id }) =>
      target_compound_id == app.data.match.visualized.ion?.target_compound_id
  )
)

const scale = ref({
  mode: 'average',
  max: null,
  log: false
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

const storedState = localStorage.getItem('match-tab-split')
const [initTop, initBottom] = JSON.parse(storedState ?? '[50, 50]')

const top = ref(initTop)
const bottom = ref(initBottom)
const heights = computed(() => [
  ((height.value - 300) * top.value) / 100,
  ((height.value - 300) * bottom.value) / 100
])
</script>

<template>
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
    <ToolbarMatchRating />
  </menu>
  <Splitter
    layout="vertical"
    stateStorage="local"
    stateKey="match-tab-split"
    style="height: calc(100vh - 200px); width: 100%"
    @resizeend="
      ({ sizes }) => {
        top = sizes[0]
        bottom = sizes[1]
      }
    "
  >
    <SplitterPanel :size="50">
      <ChartMatchSpectra v-model="scale" :sidebarOpen="sidebarOpen" :height="heights[0]" />
    </SplitterPanel>
    <SplitterPanel :size="50">
      <ChartMatchTimeseries v-model="scale" :height="heights[1]" />
    </SplitterPanel>
  </Splitter>
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
