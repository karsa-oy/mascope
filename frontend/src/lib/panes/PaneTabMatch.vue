<script setup>
import ScrollPanel from 'primevue/scrollpanel'
import Tag from 'primevue/tag'

import { computed, reactive } from 'vue'

import { ChartMatchSpectra, ChartMatchTimeseries } from '@/lib/charts'
import { ToolbarFilterIon, ToolbarMatchCharts, ToolbarMatchRating } from '@/lib/menus'
import { useAppStore, useFocusedMatch, useFilterParams, useBatchStore } from '@/stores'

const appStore = useAppStore()
const focusedMatch = useFocusedMatch()
const batchStore = useBatchStore()
const filterParams = useFilterParams()

const compound = computed(() =>
  batchStore.targetCompounds.find(
    ({ target_compound_id }) => target_compound_id == focusedMatch.ion?.target_compound_id
  )
)

const settings = reactive({
  intensityScale: null
})

const score = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})
</script>

<template>
  <div
    :style="`
      height: calc(100vh - 150px); 
      width: calc(${appStore.split.right}vw - 4rem);
    `"
  >
    <ScrollPanel style="height: calc(100vh - 150px); width: calc(100%-4rem)">
      <h1 style="text-align: center">
        <Tag
          :value="score.format(focusedMatch.ion?.match_score)"
          :severity="
            Math.abs(focusedMatch.ion?.match_score) > filterParams.current.probable_match_threshold
              ? 'danger'
              : 'success'
          "
          style="font-size: large"
        />
        match: ion <i>{{ focusedMatch.ion?.target_ion_formula }}</i>
        for
        <i>{{ focusedMatch.ion?.sample_item_name }}</i> with target
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
