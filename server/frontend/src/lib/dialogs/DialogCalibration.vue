<script setup>
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Listbox from 'primevue/listbox'
import { useConfirm } from 'primevue/useconfirm'
import { num } from '@/lib/formatters'

import { computed, watch, reactive, ref, watchEffect } from 'vue'

import { api } from '@/api'
import { useApp } from '@/stores'
import { useMzFit } from '@/lib/mzFit'
import { PaneSettingsCalibration } from '@/lib/panes'

const mzFit = useMzFit({ unmount: true })
const confirm = useConfirm()

const app = useApp()

const visible = defineModel('visible')

const props = defineProps({
  context: {
    type: Object
  }
})

const original = computed(() => props.context ?? app.data.sample.focused)
const batch = computed(() => (original.value?.sample_item_id ? null : original.value))
const samples = ref(null)
const previewSample = ref()
watchEffect(async () => {
  samples.value =
    batch.value && visible.value
      ? await api.http.get(`/samples`, {
          params: {
            sample_batch_id: batch.value.sample_batch_id,
            batch_matches_info: false,
            sort: 'datetime_utc'
          },
          use: 'read',
          type: 'load_samples'
        })
      : null
  previewSample.value = samples.value?.length > 0 ? { ...samples.value[0] } : null
})

const state = reactive({
  tab: 'info',
  previous: null
})

const title = computed(() =>
  batch.value
    ? `Calibrate batch "${original.value?.sample_batch_name}"`
    : `Calibrate sample "${original.value?.sample_item_name}"`
)

const confirmMessage = computed(() => {
  if (batch.value) {
    return `Applying calibration will remove matches for all associated samples in this and other batches. 
    This action cannot be undone. Are you sure you want to proceed?`
  }

  const batchCount = mzFit.affectedBatches?.length || 0
  const sampleCount = mzFit.affectedSamples?.length || 0

  if (batchCount > 0 || sampleCount > 0) {
    return `Applying calibration to this file will remove matches for ${sampleCount} associated 
    sample${sampleCount !== 1 ? 's' : ''} across ${batchCount} batch${batchCount !== 1 ? 'es' : ''}. 
    This action cannot be undone. Are you sure you want to proceed?`
  }

  return 'Applying calibration will affect other samples and remove existing matches. This action cannot be undone. Are you sure you want to proceed?'
})

// component initialization logic
watch(visible, init)
function init(active) {
  if (active) {
    // reset state
    state.tab = 'calibration'
    state.previous = { ...mzFit.mzCalibrationParams }
    refit()
  }
}

const unsynced = computed(() =>
  Object.keys(state.previous).some((key) => state.previous[key] !== mzFit.mzCalibrationParams[key])
)

watch(previewSample, refit)

watchEffect(() => {
  if (state.tab == 'calibration') {
    if (unsynced.value) {
      refit()
    }
  }
})

async function refit() {
  const sample = batch.value ? previewSample.value : original.value
  if (sample && visible.value) {
    await mzFit.compute(sample)
  }
  state.previous = { ...mzFit.mzCalibrationParams }
}

async function save() {
  confirm.require({
    icon: 'pi pi-exclamation-triangle',
    header: 'Confirm calibration',
    message: confirmMessage.value,
    accept: async () => {
      if (batch.value) {
        await api.http.post(
          `/calibration/mz_calibrate/batch/${original.value.sample_batch_id}`,
          mzFit.mzCalibrationParams,
          {
            use: 'process',
            type: 'recalibrate_batch'
          }
        )
      } else {
        await mzFit.apply(original.value)
      }
      visible.value = false
    },
    acceptProps: {
      label: 'Apply Calibration'
    },
    rejectProps: {
      label: 'Cancel',
      severity: 'secondary'
    }
  })
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

const columnFormatters = computed(() => ({
  mz: num.mz,
  sample_peak_mz: num.mz,
  calibration_mz: num.mz,
  match_mz_error: num.mzError,
  calibration_mz_error: num.mzError,
  mz_error_diff: num.mzError,
  calibrant_to_tic: num.ticFraction
}))

const formatter = new Intl.NumberFormat('en-US', {
  minimumIntegerDigits: 1,
  minimumFractionDigits: 1,
  maximumFractionDigits: 4
})
</script>

<template>
  <Dialog :header="title" v-model:visible="visible" style="width: 800px">
    <Tabs v-model:value="state.tab">
      <TabList>
        <Tab value="calibration">Calibration</Tab>
        <Tab value="settings">Settings</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="calibration">
          <div class="column">
            <!-- Show warning message if it exists -->
            <div class="message-container">
              <Message
                v-if="mzFit.status === 'warning'"
                severity="warn"
                style="inline-size: 400px; overflow-wrap: anywhere; margin-bottom: 1rem"
                :closable="true"
              >
                {{ mzFit.error }}
              </Message>
            </div>
            <Listbox
              v-if="samples"
              v-model:modelValue="previewSample"
              :options="samples ?? []"
              optionLabel="sample_item_name"
              dataKey="sample_item_id"
              style="height: 300px"
            />
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
                    v-if="data[col.field] !== null && data[col.field] !== undefined"
                    >{{
                      columnFormatters[col.field]
                        ? columnFormatters[col.field].format(data[col.field])
                        : formatter.format(data[col.field])
                    }}</span
                  >
                  <span v-else>-</span>
                </template>
              </Column>
            </DataTable>
            <div v-else class="center" style="height: 200px; width: 100%; overflow: hidden">
              <ProgressSpinner v-if="!(mzFit.status == 'error')" />
              <Message v-else severity="error" style="inline-size: 400px; overflow-wrap: anywhere">
                {{ mzFit.error ?? 'Calibration failed due to an unknown error.' }}
              </Message>
            </div>
          </div>
        </TabPanel>
        <TabPanel value="settings">
          <PaneSettingsCalibration v-model:mzCalibrationParams="mzFit.mzCalibrationParams" />
        </TabPanel>
      </TabPanels>
    </Tabs>
    <menu>
      <Button label="Cancel" @click="() => (visible = false)" severity="secondary" />
      <Button
        label="Save"
        :disabled="!mzFit.current || !mzFit.stats || mzFit.status === 'error'"
        @click="save"
      />
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

.message-container {
  display: flex;
  justify-content: center;
  align-items: center;
}

:deep(.p-panel-header) {
  padding-top: 0;
}
</style>
