<script setup>
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import ProgressSpinner from 'primevue/progressspinner'

import { computed, watch, reactive } from 'vue'

import { useSampleStore, useMzFit } from '@/stores'

import { PaneSettingsCalibration } from '@/lib/panes'

const mzFit = useMzFit()

const sampleStore = useSampleStore()

const visible = defineModel('visible')

const props = defineProps({
  item: {
    type: Object
  }
})

const original = computed(() => props.item ?? sampleStore.active)

const state = reactive({
  tab: 'info'
})

const title = computed(() => `Calibrate sample item "${original.value?.sample_item_name}"`)

// component initialization logic
watch(visible, init)
function init(active) {
  if (active) {
    // reset state
    state.tab = 'calibration'
    mzFit.unload()
    mzFit.compute(original.value)
  }
}

const calibration = computed(() => ({
  key: 0,
  rows: mzFit.stats ?? [],
  columns: [
    { field: 'mz', label: 'Isotope m/z' },
    { field: 'sample_peak_mz', label: 'Pre peak m/z' },
    {
      field: 'match_mz_error',
      label: 'Pre m/z error [ppm]',
      subheading: null
    },
    { field: 'calibration_mz', label: 'Post peak m/z' },
    {
      field: 'calibration_mz_error',
      label: 'Post m/z error [ppm]',
      subheading: null
    },
    { field: 'mz_error_diff', label: 'm/z error diff', subheading: null },
    {
      field: 'calibrant_to_tic',
      label: 'fraction of TIC',
      subheading: null
    }
  ]
}))

const formatter = new Intl.NumberFormat('en-US', {
  minimumIntegerDigits: 2,
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})
</script>

<template>
  <Dialog :header="title" v-model:visible="visible" style="width: 800px">
    <Message v-if="mzFit.error" severity="error">
      {{ mzFit.error }}
    </Message>

    <Tabs v-model:value="state.tab">
      <TabList>
        <Tab value="calibration">Calibration</Tab>
        <Tab value="settings">Settings</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="calibration">
          <DataTable
            v-if="calibration.rows.length > 0"
            :key="calibration.key"
            :value="
              calibration.rows.map((row, index) => ({
                ...row,
                type: index == calibration.rows.length - 1 ? 'summary' : 'stat'
              }))
            "
            sortField="mz"
            scrollable
            scrollHeight="300px"
          >
            <Column
              v-for="col of calibration.columns"
              :key="col.field"
              :field="col.field"
              :header="col.label"
            >
              <template #body="{ data }">
                <span
                  :style="data.type == 'summary' ? 'font-weight: bold' : ''"
                  v-if="data[col.field]"
                  >{{ formatter.format(data[col.field]) }}</span
                >
                <span v-else>-</span>
              </template>
            </Column>
          </DataTable>
          <div v-else class="center" style="height: 200px; width: 100%; overflow: hidden">
            <ProgressSpinner />
          </div>
        </TabPanel>
        <TabPanel value="settings">
          <PaneSettingsCalibration />
        </TabPanel>
      </TabPanels>
    </Tabs>
    <menu>
      <Button
        label="Refit"
        :disabled="!original"
        severity="info"
        @click="
          () => {
            mzFit.unload()
            mzFit.compute(original)
          }
        "
      />
      <menu>
        <Button label="Cancel" @click="() => (visible = false)" severity="secondary" />
        <Button
          label="Save"
          :disabled="!mzFit.current"
          @click="
            async () => {
              await mzFit.apply(original.filename)
              await sampleStore.matchSampleRematch(original)
              visible = false
            }
          "
        />
      </menu>
    </menu>
  </Dialog>
</template>

<style scoped>
.cols {
  display: flex;
  flex-flow: row nowrap;
  justify-content: space-around;
  gap: 0.5rem;
}

:deep(.p-panel-header) {
  padding-top: 0;
}

menu {
  justify-content: space-between;
}
</style>
