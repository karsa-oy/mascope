<script setup>
import ScrollPanel from 'primevue/scrollpanel'
import Tag from 'primevue/tag'

import { computed, reactive } from 'vue'

import { ChartMatchSpectra, ChartMatchTimeseries } from '@/lib/charts'
import { ToolbarFilterIon, ToolbarMatchCharts, ToolbarMatchRating } from '@/lib/menus'
import { useFocusedMatch, useFilterParams, useBatchStore } from '@/stores'

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
  <div style="height: calc(100vh - 150px)">
    <ScrollPanel style="height: calc(100vh - 150px)">
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
      <div class="row k-match-tools">
        <ToolbarFilterIon />
        <ToolbarMatchCharts v-model:scale="settings.intensityScale" />
        <ToolbarMatchRating />
      </div>
    </ScrollPanel>
  </div>
</template>

<style scoped>
.k-match-tools {
  position: fixed;
  top: 75px;
  right: 15px;
  z-index: 50;
  justify-content: flex-end;
  background-color: var(--p-panel-background);
  padding: 0.5rem;
  border-radius: 0.5rem;
}

.k-match-tools :deep(*) {
  margin: 0;
}
</style>
