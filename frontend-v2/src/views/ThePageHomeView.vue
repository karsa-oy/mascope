<script setup>
import { ref, computed, watch } from 'vue'

import TheLayoutSidebarView from './TheLayoutSidebarView.vue'

import BaseWorkspaceTile from '@/components/BaseWorkspaceTile.vue'
import ThePaneBrowser from '@/components/ThePaneBrowser.vue'

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

const browseAcquisitions = ref(false)
const instrumentSelected = ref([])
const sampleFileMinDatetime = ref(new Date(new Date().getTime() - 24 * 60 * 60 * 1000)) // now - 24h
const sampleFileMaxDatetime = ref(new Date()) // now
const sampleFilesSelected = ref([])
const sampleFileTableDataKey = ref(0)

instrumentSelected.value = appStore.instruments.value.filter(
  (instrument) => instrument.instrument === this.instrumentActive
)

const sampleFileCols = [{ field: 'filename', label: 'Filename' }]

const acquisitions = computed(() =>
  browseAcquisitions.value ? instrumentStore.acquisitions : instrumentStore.recentAcquisitions
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
  modalStore.sampleBatchImportProps = {
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
  modalStore.sampleItemAttributesSaveProps = {
    action: 'create',
    sampleItemRecordToLoad: this.sampleFilesSelected[0]
  }
  modalStore.activate({
    modal: 'sampleItemAttributesSave'
  })
}
function selectInstrument(newRows) {
  const instrument = newRows.length ? newRows[0].instrument : null
  if (instrument) {
    instrumentStore.load(instrument)
    getAcquisitionsInRange()
  } else {
    instrumentStore.unload()
  }
}

watch(browseAcquisitions, () => {
  // Reset selected files when switching between recent acquisitions/browse
  sampleFilesSelected.value = []
})
watch(instrumentSelected, (newRows, oldRows) => {
  // Reset selected files when switching instrument
  sampleFilesSelected.value = []
  // Allow selecting only one instrument at a time
  if (newRows === null) return
  if (newRows.length > 1) {
    instrumentSelected.value = newRows.filter((row) => !oldRows.includes(row))
    return
  }
  selectInstrument(newRows)
})
watch(sampleFileMinDatetime, () => {
  getAcquisitionsInRange()
})
watch(sampleFileMaxDatetime, () => {
  getAcquisitionsInRange()
})
watch(instrumentStore.recentAcquisitions, () => {
  // This watcher triggers on database reload
  if (browseAcquisitions.value) getAcquisitionsInRange()
})
</script>

<template>
  <section>
    <the-layout-sidebar-view>
      <div class="columns" style="margin: 0 auto; width: 70vw">
        <div class="column is-half">
          <section style="padding: 2em 2em 2em 2em">
            <h1 class="title is-4">Instruments:</h1>
          </section>
          <h2>Select instrument to monitor</h2>
          <b-table
            :data="instruments"
            :columns="[{ field: 'instrument', label: 'Instrument' }]"
            checkable
            :header-checkable="false"
            v-model:checked-rows="instrumentSelected"
          >
          </b-table>
          <div v-if="instrumentActive">
            <section style="padding: 2em 2em 2em 2em">
              <h1 class="title is-4">Acquisitions:</h1>
            </section>
            <b-collapse v-model:open="browseAcquisitions" animation="slide">
              <template #trigger>
                <section style="padding: 0.5em">
                  <b-button
                    icon-left="calendar"
                    size="is-small"
                    @click="
                      (props) => {
                        props.open = !props.open
                      }
                    "
                  >
                  </b-button>
                </section>
              </template>
              <div class="columns">
                <div class="column is-half">
                  <b-datetimepicker placeholder="Starting from..." v-model="sampleFileMinDatetime">
                  </b-datetimepicker>
                </div>
                <div class="column is-half">
                  <b-datetimepicker placeholder="Until..." v-model="sampleFileMaxDatetime">
                  </b-datetimepicker>
                </div>
              </div>
            </b-collapse>
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
                :disabled="
                  !workspaceStore.active || !batchStore.active || sampleFilesSelected.length != 1
                "
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
        </div>
        <div class="column is-half">
          <template v-if="!workspaceStore.active">
            <section style="padding: 2em 2em 2em 2em">
              <h1 class="title is-4">Workspaces:</h1>
            </section>
            <section class="base-tile-container">
              <base-workspace-tile
                v-for="workspace in appStore.workspaces"
                :key="workspace.id"
                :workspace="workspace"
              ></base-workspace-tile>
            </section>
            <section style="padding: 0.5em">
              <b-button
                type="is-primary"
                style="position: fixed; right: 5em; bottom: 2em"
                @click="
                  () => {
                    modalStore.workspaceSaveProps = {
                      action: 'create'
                    }
                    modalStore.activate({
                      modal: 'workspaceSave'
                    })
                  }
                "
              >
                Create workspace
              </b-button>
            </section>
          </template>
          <template v-else>
            <the-pane-browser></the-pane-browser>
          </template>
        </div>
      </div>
    </the-layout-sidebar-view>
  </section>
</template>

<style scoped>
.base-home-page {
  display: flex;
  flex-flow: column nowrap;
  min-height: 100vh;
  max-width: 1190px;
  padding: 2em;
}

.base-tile-container {
  flex: 1;
  display: flex;
  flex-flow: row wrap;
  justify-content: flex-start;
  align-content: flex-start;
  gap: 10px 10px;
}
</style>
