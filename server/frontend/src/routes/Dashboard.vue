<script setup>
import { computed } from 'vue'

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
  PaneBrowserMatch,
  PaneTabMatch,
  PaneTabAcquisitions,
  PaneTabSample,
  PaneTabBatch
} from '@/lib/panes'
import { HelpButton, HelpPopover } from '@/lib/help'

import { useApp } from '@/stores'

const app = useApp()

const tabs = computed(() => [
  {
    label: 'Acquisitions',
    icon: 'pi pi-hourglass',
    help: `
      <h1>Acquisitions</h1>
      <p>
        View data files uploaded to the Mascope server, and import files from your computer.
      </p>
      <p>
        Process files retrospectively into samples and batches.
      </p>
    `
  },
  {
    label: 'Batch',
    icon: 'pi pi-hashtag',
    disabled: !app.data.batch.focused || app.data.sample.list.length === 0,
    help: `
      <h1>Batch View</h1>

      <p>
        Visualize the currently selected batch. Select a target 
        collection to view the matches found in each sample in the batch.
      </p>

      <p>
        Drag with mouse to zoom in, or pick the Select-tool to select samples by
        dragging instead. Chart tools are available at top-right. Double click to reset zoom.
      </p>  

      <p>Click on a data point to visualize the corresponding Match.</p>

      <p>
        Chart settings (top-left) allow you to select the x-axis dimension, y-axis scaling etc.
      </p>
    `
  },
  {
    label: 'Sample',
    icon: 'pi pi-chart-bar',
    disabled: !app.data.sample.focused,
    help: `
      <h1>Sample View</h1>

      <p>Visualize the selected sample's spectrum and peaks.</p>

      <p>Assign elemental composition to detected peaks and add them to a target collection.</p>
    `
  },
  {
    label: 'Match',
    icon: 'pi pi-wave-pulse',
    disabled: !app.data.match.visualized.ion,
    help: `
      <h1>Match View</h1>
      <p>
        Visualize the currently selected ion match for the selected sample.
        Displays the spectrum for each matched isotope as well as the timeseries
        of matched peaks.
      </p>
      <p>
        Shows match metrics (intensity, m/z error, isotope abundance error) while hovering over the chart.
        You may tweak matching parameters in the settings panel (top-left) to fine-tune matching.
      </p>
    `
  }
])
</script>

<template>
  <article style="position: relative">
    <menu id="filters">
      <ToolbarAppFilters />
    </menu>
    <div style="position: absolute; top: 80px; right: 1rem; z-index: 100">
      <HelpButton />
    </div>
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
      <SplitterPanel :size="app.ui.split.left">
        <Splitter
          layout="vertical"
          stateStorage="local"
          stateKey="mascope-browser-split"
          @resize="
            ({ sizes }) => {
              app.ui.split.top = sizes[0]
              app.ui.split.bottom = sizes[1]
            }
          "
        >
          <SplitterPanel :size="app.ui.split.top">
            <PaneBrowserSample />
          </SplitterPanel>
          <SplitterPanel :size="app.ui.split.bottom">
            <PaneBrowserMatch />
          </SplitterPanel>
        </Splitter>
      </SplitterPanel>
      <SplitterPanel :size="app.ui.split.right">
        <Panel id="charts">
          <Tabs v-model:value="app.ui.tab.active">
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
              <TabPanel value="acquisitions">
                <PaneTabAcquisitions :active="app.ui.tab.active == 'acquisitions'" />
              </TabPanel>
              <TabPanel value="batch">
                <PaneTabBatch :active="app.ui.tab.active == 'batch'" />
              </TabPanel>
              <TabPanel value="sample" :pt="{ content: { style: { padding: 0 } } }">
                <PaneTabSample v-if="app.ui.tab.active == 'sample'" />
              </TabPanel>
              <TabPanel value="match" :pt="{ content: { style: { padding: 0 } } }">
                <PaneTabMatch />
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
