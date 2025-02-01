<script setup>
import { ref, computed } from 'vue'

import Splitter from 'primevue/splitter'
import SplitterPanel from 'primevue/splitterpanel'
import Panel from 'primevue/panel'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'

import { ToolbarAppFilters } from '@/lib/toolbars'
import {
  PaneProgress,
  PaneBrowserSample,
  PaneBrowserTarget,
  PaneTabMatch,
  PaneTabAcquisitions
} from '@/lib/panes'
import { ChartBatchOverview, ChartSampleSpectrum } from '@/lib/charts'
import { HelpPopover } from '@/lib/help'

import { useApp } from '@/stores'

const app = useApp()

const tabs = computed(() => [
  {
    label: 'Acquisitions',
    icon: 'pi pi-hourglass',
    help: `
      <h1>Acquisition Table</h1>

      <p>View incoming measurements and import them
      into batches. Import files from your computer
      into Mascope.</p>
    `
  },
  {
    label: 'Batch',
    icon: 'pi pi-hashtag',
    disabled: app.data.sample.list.length == 0,
    help: `
      <h1>Batch Overview Chart</h1>

      <p>Visualize intensity of all samples in
      a batch against various data points.</p>
    `
  },
  {
    label: 'Spectrum',
    icon: 'pi pi-chart-bar',
    disabled: !app.data.sample.focused,
    help: `
      <h1>Sample Spectrum Chart</h1>

      <p>Visualize the selected sample's signal
      in detail.</p>
    `
  },
  {
    label: 'Match',
    icon: 'pi pi-wave-pulse',
    disabled: !app.data.match.visualized.ion,
    help: `
      <h1>Match Overview</h1>

      <p>Visualize match isotope peaks for a
      selected ion as well as their timeseries.
      Adjust match parameters to fine-tune matches.</p>
    `
  }
])
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
            <PaneBrowserTarget />
          </SplitterPanel>
        </Splitter>
      </SplitterPanel>
      <SplitterPanel :size="80">
        <Panel id="charts">
          <Tabs v-model:value="app.ui.tab.active" lazy>
            <TabList>
              <Tab
                v-for="{ icon, label, disabled, help } in tabs"
                :value="label.toLowerCase()"
                :key="label"
                :disabled="disabled"
                :pt="app.ui.help.bottom(help)"
              >
                <div class="row">
                  <span :class="icon" /><span>{{ label }}</span>
                </div>
              </Tab>
            </TabList>
            <TabPanels>
              <TabPanel value="batch">
                <ChartBatchOverview />
              </TabPanel>
              <TabPanel value="spectrum">
                <ChartSampleSpectrum />
              </TabPanel>
              <TabPanel value="match">
                <PaneTabMatch v-if="app.data.match.visualized.ion" />
              </TabPanel>
              <TabPanel value="acquisitions">
                <PaneTabAcquisitions :active="app.ui.tab.active == 'acquisitions'" />
              </TabPanel>
            </TabPanels>
          </Tabs>
        </Panel>
      </SplitterPanel>
    </Splitter>
    <PaneProgress />
    <HelpPopover />
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
  border: none;
  height: calc(100% -10rem);
}

#charts :deep(.p-panel-header) {
  display: none;
}

menu {
  padding: 0;
  margin: 0;
}
menu > :deep(*) {
  height: 60px;
}
</style>
