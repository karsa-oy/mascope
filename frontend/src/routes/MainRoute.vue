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

import { ToolbarAppFilters } from '@/lib/toolbars'
import {
  PaneProgress,
  PaneBrowserSample,
  PaneBrowserTarget,
  PaneTabMatch,
  PaneTabAcquisitions
} from '@/lib/panes'
import { ChartBatchOverview, ChartSampleSpectrum } from '@/lib/charts'

import { useApp } from '@/stores'

const app = useApp()

const tabs = computed(() => [
  {
    label: 'Batch',
    icon: 'pi pi-hashtag'
  },
  {
    label: 'Spectrum',
    icon: 'pi pi-chart-bar',
    disabled: !app.data.sample.focused
  },
  {
    label: 'Match',
    icon: 'pi pi-wave-pulse',
    disabled: !app.ui.matchVisualized.ion
  },
  {
    label: 'Acquisitions',
    icon: 'pi pi-hourglass',
    disabled: !app.data.instrument.focused
  }
])

watch(
  computed(() => app.data.acquisition.mode),
  (scenthound) => {
    if (scenthound) {
      app.ui.tab.active = 'acquisitions'
    }
  }
)
watch(
  computed(() => app.ui.matchVisualized.ion),
  (focused) => {
    if (focused && app.ui.tab.active !== 'spectrum') {
      app.ui.tab.active = 'match'
    } else {
      if (app.ui.tab.active == 'match') {
        app.ui.tab.active = 'batch'
      }
    }
  }
)
watch(
  computed(() => app.data.sample.focused),
  (sample) => {
    if (!sample && app.ui.tab.active == 'spectrum') {
      app.ui.tab.active = 'batch'
    }
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
          app.ui.split.left = sizes[0]
          app.ui.split.right = sizes[1]
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
          <Tabs v-model:value="app.ui.tab.active">
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
                <ChartBatchOverview v-if="app.data.batch.focused" />
              </TabPanel>
              <TabPanel value="spectrum">
                <ChartSampleSpectrum />
              </TabPanel>
              <TabPanel value="match">
                <PaneTabMatch v-if="app.ui.matchVisualized.ion" />
              </TabPanel>
              <TabPanel value="acquisitions">
                <PaneTabAcquisitions
                  v-if="app.data.instrument.focused"
                  :active="app.ui.tab.active == 'acquisitions'"
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
