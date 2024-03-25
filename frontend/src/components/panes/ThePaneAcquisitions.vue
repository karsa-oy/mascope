<script setup>
import { ref, computed, watch } from 'vue'

import {
  useAppStore,
  useBatchStore,
  useModalStore,
  useSampleStore,
  useWorkspaceStore,
  useInstrumentStore
} from '@/stores'

const appStore = useAppStore()
const batchStore = useBatchStore()
const sampleStore = useSampleStore()
const modalStore = useModalStore()
const workspaceStore = useWorkspaceStore()
const instrumentStore = useInstrumentStore()

const mode = ref('recent')
const instrumentSelected = ref(instrumentStore.active ?? appStore.instruments[0].instrument)
const sampleFileMinDatetime = ref(new Date(new Date().getTime() - 24 * 60 * 60 * 1000)) // now - 24h
const sampleFileMaxDatetime = ref(new Date()) // now
const sampleFilesSelected = ref([])
const sampleFileTableDataKey = ref(0)

instrumentStore.load(instrumentSelected.value)
getAcquisitionsInRange()

const sampleFileCols = [{ field: 'filename', label: 'Filename' }]

const showRecent = computed(() => mode.value == 'recent')
const acquisitions = computed(() =>
  showRecent.value ? instrumentStore.recentAcquisitions : instrumentStore.acquisitions
)

function getAcquisitionsInRange() {
  // Reset selected files when changing range, to avoid ghost selections
  sampleFilesSelected.value = []
  instrumentStore.getAcquisitions({
    min: sampleFileMinDatetime.value,
    max: sampleFileMaxDatetime.value
  })
}
function launchProcessBatchModal() {
  modalStore.state.sampleBatchImportProps = {
    sampleFilesSelected: sampleFilesSelected.value
  }
  modalStore.activate({
    modal: 'sampleBatchImport'
  })
}
function launchProcessSelectedModal() {
  // defocus currently focused sample
  if (sampleStore.active) {
    batchStore.sampleItemFocus(sampleStore.active)
  }
  modalStore.state.sampleItemAttributesSaveProps = {
    action: 'create',
    sampleItemRecordToLoad: sampleFilesSelected.value[0]
  }
  modalStore.activate({
    modal: 'sampleItemAttributesSave'
  })
}

watch(showRecent, () => {
  // Reset selected files when switching between recent acquisitions/browse
  sampleFilesSelected.value = []
})
watch(instrumentSelected, (instrument) => {
  if (instrument) {
    instrumentStore.load(instrument)
    getAcquisitionsInRange()
  } else {
    instrumentStore.unload()
  }
})
watch(sampleFileMinDatetime, () => {
  getAcquisitionsInRange()
})
watch(sampleFileMaxDatetime, () => {
  getAcquisitionsInRange()
})
watch(
  computed(() => instrumentStore.recentAcquisitions),
  () => {
    // This watcher triggers on database reload
    if (!showRecent.value) getAcquisitionsInRange()
  }
)
</script>

<template>
  <h1 class="title is-5">Acquisitions</h1>
  <div class="row">
    <span>Instrument: </span>
    <b-dropdown v-model="instrumentSelected" paddingless aria-role="list">
      <template #trigger>
        <b-button type="is-primary" icon-right="menu-down">
          {{ instrumentSelected ?? 'none' }}
        </b-button>
      </template>
      <template
        v-for="instrument in appStore.instruments.map(({ instrument }) => instrument)"
        v-bind:key="instrument"
      >
        <b-dropdown-item :value="instrument" aria-role="listitem">
          <span>{{ instrument }}</span>
        </b-dropdown-item>
      </template>
    </b-dropdown>
  </div>
  <div class="row">
    <b-radio v-model="mode" native-value="recent"> Show recent </b-radio>
    <b-radio v-model="mode" native-value="timerange"> Browse timerange </b-radio>
  </div>
  <div v-if="instrumentStore.active">
    <div v-if="!showRecent">
      <div class="row">From: <b-datetimepicker v-model="sampleFileMinDatetime" /></div>
      <div class="row">
        To:
        <b-datetimepicker v-model="sampleFileMaxDatetime" />
      </div>
    </div>
    <b-table
      :key="sampleFileTableDataKey"
      :data="acquisitions ? acquisitions : []"
      :columns="sampleFileCols"
      checkable
      v-model:checked-rows="sampleFilesSelected"
    >
    </b-table>
    <section style="padding: 0.5em">
      <b-button
        type="is-primary"
        style="position: fixed; left: 5em; bottom: 2em"
        :disabled="!workspaceStore.active || !batchStore.active || sampleFilesSelected.length != 1"
        @click="launchProcessSelectedModal"
      >
        Process file
      </b-button>
      <b-button
        v-if="browseAcquisitions || sampleFilesSelected.length > 1"
        type="is-primary"
        style="position: fixed; left: 15em; bottom: 2em"
        :disabled="
          !workspaceStore.active ||
          !batchStore.active ||
          acquisitions === null ||
          !acquisitions.length ||
          sampleFilesSelected.length == 0
        "
        @click="launchProcessBatchModal"
      >
        Process batch ({{ sampleFilesSelected ? sampleFilesSelected.length : 0 }})
      </b-button>
    </section>
  </div>
</template>

<style scope>
.row {
  display: flex;
  flex-flow: row nowrap;
  justify-content: space-between;
  margin: 1rem 0;
  width: 100%;
  max-width: 350px;
}
</style>
