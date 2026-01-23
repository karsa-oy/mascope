<script setup>
import { computed, ref } from 'vue'

import Splitter from 'primevue/splitter'
import SplitterPanel from 'primevue/splitterpanel'

import { useWindowSize } from '@vueuse/core'

import { BaseMatchTag } from '@/lib/base'
import { ChartMatchSpectra, ChartMatchTimeseries } from '@/lib/charts'
import { ToolbarMatchRating } from '@/lib/toolbars'
import { useApp } from '@/stores'

import SidebarMatchParams from './SidebarMatchParams.vue'

const { height } = useWindowSize()

const app = useApp()

const scale = ref({
  mode: 'average',
  max: null,
  log: false
})

// Compute UI-based match category for display
const uiMatchCategory = computed(() => {
  const ion = app.data.match.visualized.ion
  if (!ion?.match) return

  return app.data.match.params.uiCategory(ion.match)
})

const sidebarOpen = ref(false)

const storedState = localStorage.getItem('match-tab-split')
const [initTop, initBottom] = JSON.parse(storedState ?? '[50, 50]')

const top = ref(initTop)
const bottom = ref(initBottom)
const heights = computed(() => [
  ((height.value - 350) * top.value) / 100,
  ((height.value - 350) * bottom.value) / 100
])
</script>

<template>
  <div class="pane-wrapper">
    <menu class="topbar">
      <div>
        <SidebarMatchParams v-model:open="sidebarOpen" />
      </div>
      <h1>
        <BaseMatchTag
          :matchScore="app.data.match.visualized.ion?.match?.match_score"
          :matchCategory="uiMatchCategory"
          :alarming="app.data.match.visualized.ion?.match?.alarming"
          :style="'font-size: large'"
        />
        {{ app.data.match.visualized.ion ? 'Ion ' : '' }}
        <i>{{ app.data.match.visualized.ion?.target_ion_formula }}</i>
        {{ app.data.match.visualized.ion ? ' of compound ' : '' }}
        <i>{{ app.data.match.visualized.ion?.target_compound_formula }}</i>
      </h1>
      <ToolbarMatchRating />
    </menu>
    <Splitter
      layout="vertical"
      stateStorage="local"
      stateKey="match-tab-split"
      class="match-splitter"
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
  </div>
</template>

<style scoped>
.match-splitter {
  flex: 1;
  min-height: 0;
  width: 100%;
}

.topbar {
  width: 100%;
  max-width: 100%;
  display: flex;
  flex-flow: row wrap;
  justify-content: space-between;
  align-items: flex-start;
  margin: 0;
  padding: 0;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  flex-shrink: 0;

  h1 {
    margin: 0;
    padding: 0;
    padding-top: 0.5rem;
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: normal;
    text-align: center;
  }
}
</style>
