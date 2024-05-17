<script setup>
import { ref, computed, watch } from 'vue'

import Splitter from 'primevue/splitter'
import SplitterPanel from 'primevue/splitterpanel'

import { ToolbarAppFilters } from '@/lib/menus'
import {
  PaneProgress,
  PaneBrowserSample,
  PaneBrowserTarget,
  PaneDashSignal,
  PaneAcquisitions
} from '@/lib/panes'
import { ChartBatchOverview } from '@/lib/charts'

import {
  useAppStore,
  useBatchStore,
  useVisualizationStore,
  useInstrumentStore,
  useWorkspaceStore,
  useSampleStore,
  useTargetsStore
} from '@/stores'

const appStore = useAppStore()
const workspaceStore = useWorkspaceStore()
const batchStore = useBatchStore()
const sampleStore = useSampleStore()
const visualizationStore = useVisualizationStore()
const instrumentStore = useInstrumentStore()
const targetsStore = useTargetsStore()

const tab = ref(0)
const tabs = computed(() => [
  {
    label: 'Batch',
    icon: 'pi pi-hashtag'
  },
  {
    label: 'Match',
    icon: 'pi pi-wave-pulse',
    disabled: !visualizationStore.activeIon
  },
  {
    label: 'Acquisitions',
    icon: 'pi pi-hourglass',
    disabled: !instrumentStore.active
  }
])

watch(
  computed(() => appStore.mode.measuring),
  (scenthound) => {
    if (scenthound) {
      tab.value = 2
    }
  }
)
watch(
  computed(() => visualizationStore.activeIon),
  (visualization) => {
    if (!visualization) {
      tab.value = 0
    } else {
      tab.value = 1
    }
  }
)
watch(
  computed(() => workspaceStore.active),
  () => {
    batchStore.unload()
    sampleStore.unload()
    targetsStore.unload()
  }
)
</script>

<template>
  <article>
    <menu id="filters">
      <ToolbarAppFilters />
    </menu>
    <Splitter
      style="grid-area: dashboard; height: 100%"
      stateStorage="local"
      stateKey="mascope-dashboard-split"
      @resize="
        ({ sizes }) => {
          appStore.split.left = sizes[0]
          appStore.split.right = sizes[1]
        }
      "
    >
      <SplitterPanel :size="20">
        <Splitter layout="vertical" stateStorage="local" stateKey="mascope-browser-split">
          <SplitterPanel :size="50">
            <PaneBrowserSample />
          </SplitterPanel>
          <SplitterPanel :size="50">
            <PaneBrowserTarget @focused="tab = 1" />
          </SplitterPanel>
        </Splitter>
      </SplitterPanel>
      <SplitterPanel :size="80">
        <Panel id="charts" class="k-browser" style="border: none">
          <template #header>
            <TabMenu v-model:activeIndex="tab" :model="tabs" />
          </template>
          <ChartBatchOverview v-if="tab == 0 && batchStore.active" />
          <PaneDashSignal v-if="tab == 1 && visualizationStore.activeIon" />
          <PaneAcquisitions v-if="tab == 2 && instrumentStore.active" :active="tab == 2" />
        </Panel>
      </SplitterPanel>
    </Splitter>
    <PaneProgress />
  </article>
</template>

<style scoped>
article {
  width: 100%;
  max-width: 100%;
  height: 100vh;
  max-height: 100vh;
  display: grid;
  grid-template-rows: 60px calc(100vh - 65px - 2rem) 5px;
  grid-template-columns: 1fr;
  grid-template-areas:
    'filters'
    'dashboard'
    'progress';
  gap: 0.5rem;
  padding: 0.5rem;
}
#filters {
  grid-area: filters;
}
#charts {
  grid-area: charts;
}
menu {
  padding: 0;
  margin: 0;
}
menu > :deep(*) {
  height: 60px;
}
</style>
