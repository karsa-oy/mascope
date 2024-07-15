<script setup>
import { computed, watch } from 'vue'

import Splitter from 'primevue/splitter'
import SplitterPanel from 'primevue/splitterpanel'
import Panel from 'primevue/panel'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'

import { ToolbarAppFilters } from '@/lib/menus'
import {
  PaneProgress,
  PaneBrowserSample,
  PaneBrowserTarget,
  PaneTabMatch,
  PaneTabAcquisitions
} from '@/lib/panes'
import { ChartBatchOverview, ChartSampleSpectrum } from '@/lib/charts'

import {
  useAppStore,
  useBatchStore,
  useFocusedMatch,
  useInstrumentStore,
  useWorkspaceStore,
  useSampleStore,
  useTargetsStore,
  useDashboard
} from '@/stores'

const appStore = useAppStore()
const workspaceStore = useWorkspaceStore()
const batchStore = useBatchStore()
const sampleStore = useSampleStore()
const focusedMatch = useFocusedMatch()
const instrumentStore = useInstrumentStore()
const targetsStore = useTargetsStore()

const dashboard = useDashboard()

const tabs = computed(() => [
  {
    label: 'Batch',
    icon: 'pi pi-hashtag'
  },
  {
    label: 'Spectrum',
    icon: 'pi pi-chart-bar',
    disabled: !sampleStore.active
  },
  {
    label: 'Match',
    icon: 'pi pi-wave-pulse',
    disabled: !focusedMatch.ion
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
      dashboard.tab = 'acquisitions'
    }
  }
)
watch(
  computed(() => focusedMatch.ion),
  (focused) => {
    if (focused && dashboard.tab !== 'spectrum') {
      dashboard.tab = 'match'
    } else {
      if (dashboard.tab == 'match') {
        dashboard.tab = 'batch'
      }
    }
  }
)
watch(
  computed(() => sampleStore.active),
  (sample) => {
    if (!sample && dashboard.tab == 'spectrum') {
      dashboard.tab = 'batch'
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
        <Panel id="charts" class="browser" style="border: none">
          <Tabs v-model:value="dashboard.tab">
            <TabList>
              <Tab
                v-for="{ icon, label, disabled } in tabs"
                :value="label.toLowerCase()"
                :key="label"
                :disabled="disabled"
              >
                <div class="row">
                  <span :class="icon" /><span>{{ label }}</span>
                </div>
              </Tab>
            </TabList>
            <TabPanels>
              <TabPanel value="batch">
                <ChartBatchOverview v-if="batchStore.active" />
              </TabPanel>
              <TabPanel value="spectrum">
                <ChartSampleSpectrum />
              </TabPanel>
              <TabPanel value="match">
                <PaneTabMatch v-if="focusedMatch.ion" />
              </TabPanel>
              <TabPanel value="acquisitions">
                <PaneTabAcquisitions
                  v-if="instrumentStore.active"
                  :active="dashboard.tab == 'acquisitions'"
                />
              </TabPanel>
            </TabPanels>
          </Tabs>
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
