<script setup>
import * as _ from 'underscore'

import { computed, ref } from 'vue'
import { generateCopyName } from '@/api'

import {
  useAppStore,
  useWorkspaceStore,
  useBatchStore,
  useModalStore,
  useTargetsStore,
  useNotificationStore
} from '@/stores'

const appStore = useAppStore()
const workspaceStore = useWorkspaceStore()
const batchStore = useBatchStore()
const modalStore = useModalStore()
const targetsStore = useTargetsStore()
const notificationStore = useNotificationStore()

// Main batch data

// Basic fields
const batchName = ref('')
const batchDesc = ref('')
// Selected Associations data
const calibrationCollectionSelected = ref(null)
const targetCollectionsSelected = ref([])
const ionMechanismsSelected = ref([])

// Utility data

const activeTab = ref(null) // This will hold the value of the active tab
const isCopying = ref(false)
// Basic fields to track changes
const initialBatchName = ref('')
const initialBatchDesc = ref('')
// Calibration tab
const selectedCalibrationCollectionType = ref('calibrants') // default calibrant selection
const initialCalibrationCollection = ref(null) // This will be used to check if the user has changed the calibration collection
// Target Collections tab
const selectedTargetCollectionType = ref('all') // default target selection
const initialTargetCollections = ref([]) // To store initial target collections
// Ionization tab
const initialIonizationMechanisms = ref([]) // To store initial ion_mechanisms

// copy action
const workspaceSelected = ref(null)
const newBatchName = ref(batchStore.active ? `${batchStore.active.sample_batch_name} Copy` : null)
const newBatchDescription = ref(
  batchStore.active ? batchStore.active.sample_batch_description : null
)

//// General data ////

const action = computed(() => modalStore.state.sampleBatchOpProps.action)

const collectionColumns = computed(() => {
  return [
    { field: 'target_collection_name', label: 'Name' },
    { field: 'target_collection_description', label: 'Description' }
  ]
})
const calibrationTabDisabled = computed(() => {
  switch (action.value) {
    case 'create':
      return false
    default:
      return true
  }
})

const saveButtonDisabled = computed(() => {
  switch (action.value) {
    case 'create':
      return (
        !batchName.value ||
        !calibrationCollectionSelected.value ||
        ionMechanismsSelected.value.length === 0
      )

    case 'update': {
      // Check if basic properties have changed
      const basicPropertiesChanged =
        (batchName.value !== initialBatchName.value ||
          batchDesc.value !== initialBatchDesc.value) &&
        batchName.value // the name is required

      // Compare initial and current calibration collection

      const calibrationCollectionChanged =
        initialCalibrationCollection.value?.target_collection_id !==
        calibrationCollectionSelected.value?.target_collection_id

      // Compare initial and current target collections
      const collectionsChanged =
        initialTargetCollections.value
          .map((collection) => collection.target_collection_id)
          .sort()
          .join() !==
        targetCollectionsSelected.value
          .map((collection) => collection.target_collection_id)
          .sort()
          .join()

      // Compare initial and current ion mechanisms
      const ionMechanismsChanged =
        !_.isEqual(
          initialIonizationMechanisms.value.map((mechanism) => mechanism).sort(),
          ionMechanismsSelected.value.map((mechanism) => mechanism).sort()
        ) && ionMechanismsSelected.value.length > 0 // Check if there are any ion_mechanisms selected

      return (
        !basicPropertiesChanged &&
        !calibrationCollectionChanged &&
        !collectionsChanged &&
        !ionMechanismsChanged
      )
    }
    case 'editBatchCollections':
      // Compare initial and current target collections
      return (
        initialTargetCollections.value
          .map((collection) => collection.target_collection_id)
          .sort()
          .join() ==
        targetCollectionsSelected.value
          .map((collection) => collection.target_collection_id)
          .sort()
          .join()
      )

    default:
      return false
  }
})
//// Labels and titles ////
const modalTitle = computed(() => {
  switch (action.value) {
    case 'create':
      return `Create a new sample batch`
    case 'update':
      return `Update sample batch "${batchName.value}"`
    case 'editBatchCollections':
      return `Edit collections of sample batch "${batchName.value}"`
    case 'delete':
      return `Delete sample batch "${batchName.value}"`
    case 'copy':
      return `Copy sample batch "${batchName.value}"`
    default:
      return 'Unknown sample batch operation'
  }
})
/// Calibration Tab ////
const displayedCalibrationCollections = computed(() => {
  switch (selectedCalibrationCollectionType.value) {
    case 'targets':
      return targetsStore.getTargetsCollections
    case 'calibrants':
      return targetsStore.getCalibrantsCollections
    case 'diagnostics':
      return targetsStore.getDiagnosticsCollections
    case 'all':
    default:
      return targetsStore.getAllCollections
  }
})
/// Target Collections Tab ////
const displayedTargetCollections = computed(() => {
  switch (selectedTargetCollectionType.value) {
    case 'targets':
      return targetsStore.getTargetsCollections
    case 'calibrants':
      return targetsStore.getCalibrantsCollections
    case 'diagnostics':
      return targetsStore.getDiagnosticsCollections
    case 'all':
    default:
      return targetsStore.getAllCollections
  }
})

/// Copy batch action ////
const sameWorkspace = computed(() => {
  return workspaceStore.active ? workspaceStore.active : null
})
const filteredWorkspaces = computed(() => {
  if (workspaceStore.active) {
    return appStore.workspaces.filter((workspace) => {
      return workspace.workspace_id !== workspaceStore.active.workspace_id
    })
  }
  return []
})
//// data to form http request ////
const ionMechanismIds = computed(() => {
  return ionMechanismsSelected.value.map((row) => row.ionization_mechanism_id)
})
const targetCollectionIds = computed(() => {
  return targetCollectionsSelected.value.map((row) => row.target_collection_id)
})
const newBatch = computed(() => {
  if (action.value == 'create') {
    return {
      sample_batch_name: batchName.value,
      sample_batch_description: batchDesc.value,
      workspace_id: workspaceStore.active.workspace_id,
      build_params: {
        calibration_collection: calibrationCollectionSelected.value.target_collection_id,
        ion_mechanisms: ionMechanismIds.value
      },
      target_collection_ids: targetCollectionIds.value
    }
  }
  if (action.value == 'update' || action.value == 'editBatchCollections') {
    return {
      sample_batch_id: batchStore.active.sample_batch_id,
      sample_batch_name: batchName.value,
      sample_batch_description: batchDesc.value,
      workspace_id: workspaceStore.active.workspace_id,
      build_params: {
        calibration_collection: calibrationCollectionSelected.value.target_collection_id,
        ion_mechanisms: ionMechanismIds.value
      },
      target_collection_ids: targetCollectionIds.value,
      sample_batch_utc_created: batchStore.active.sample_batch_utc_created
    }
  }
  return null
})

async function deleteSampleBatch(batch) {
  batchStore.unload()
  await batchStore.deleteBatch(batch)
}
async function copySampleBatch() {
  isCopying.value = true
  const batchCopyData = {
    // for http client
    sample_batch_id: batchStore.active.sample_batch_id,
    workspace_id: workspaceSelected.value.workspace_id,
    sample_batch_name: newBatchName.value,
    sample_batch_description: newBatchDescription.value,
    // for notification
    workspace_name: workspaceSelected.value.workspace_name
  }
  await batchStore.copyBatch(batchCopyData)
  isCopying.value = false
  modalStore.deactivate()
}

//// Data loading ////
// General data loading methods
function initData() {
  // Initialization logic when the modal is activated
  if (action.value == 'create') {
    activeTab.value = 'info'
    selectedTargetCollectionType.value = 'targets'
    selectedCalibrationCollectionType.value = 'calibrants'
    batchName.value = ''
    batchDesc.value = ''
    // TODO_configuration
    // set defaults
    let calibrantTargets = displayedCalibrationCollections.value.find(
      (collection) => collection.target_collection_name === 'Br calibrants'
    )
    calibrationCollectionSelected.value = calibrantTargets
      ? calibrantTargets
      : targetsStore.getAllCollections.find(
          (collection) => collection.target_collection_id === 'xkSPp3eZrWXYSVDa'
        )
    let explosivesTargets = displayedTargetCollections.value.filter(
      (collection) => collection.target_collection_name === 'Explosives targets'
    )
    targetCollectionsSelected.value =
      explosivesTargets.length > 0
        ? explosivesTargets
        : targetsStore.getAllCollections.filter(
            (collection) => collection.target_collection_id === 'kNBOCx32dpehRWUw'
          )
    ionMechanismsSelected.value = appStore.ionMechanisms.filter(
      (mech) => mech.ionization_mechanism === '+Br-'
    )
  }
  if (action.value == 'update') {
    activeTab.value = 'info'
    selectedTargetCollectionType.value = 'targets'
    selectedCalibrationCollectionType.value = 'calibrants'
    batchName.value = batchStore.active.sample_batch_name
    batchDesc.value = batchStore.active.sample_batch_description
    initialBatchName.value = batchName.value
    initialBatchDesc.value = batchDesc.value
    initCalibrationCollectionSelected()
    initTargetCollectionsSelected()
    initIonMechanismsSelected()
  }
  if (action.value == 'delete') {
    batchName.value = batchStore.active.sample_batch_name
  }
  if (action.value == 'copy') {
    batchName.value = batchStore.active.sample_batch_name
    newBatchName.value = batchStore.active
      ? generateCopyName(batchStore.active.sample_batch_name)
      : null
    newBatchDescription.value = batchStore.active.sample_batch_description
    workspaceSelected.value = null
  }
  if (action.value == 'editBatchCollections') {
    activeTab.value = 'collections'
    selectedTargetCollectionType.value = 'all'
    selectedCalibrationCollectionType.value = 'calibrants'
    batchName.value = batchStore.active.sample_batch_name
    batchDesc.value = batchStore.active.sample_batch_description
    initCalibrationCollectionSelected()
    initTargetCollectionsSelected()
    initIonMechanismsSelected()
  }
}
function initCalibrationCollectionSelected() {
  // set active batch calibration collection from build_params
  if (batchStore.paramCalibrationCollection) {
    calibrationCollectionSelected.value = targetsStore.getAllCollections.find(
      (collection) => collection.target_collection_id == batchStore.paramCalibrationCollection
    )
  }
  initialCalibrationCollection.value = calibrationCollectionSelected.value
  if (!calibrationCollectionSelected.value) {
    // set defaults if batch calibration collection is not set (debug)
    // TODO_configuration
    let calibrantTargets = displayedCalibrationCollections.value.find(
      (collection) => collection.target_collection_name === 'Br calibrants'
    )
    calibrationCollectionSelected.value = calibrantTargets
      ? calibrantTargets
      : targetsStore.getAllCollections.find(
          (collection) => collection.target_collection_id === 'xkSPp3eZrWXYSVDa'
        )
    const data = {
      batchName: batchName.value,
      collectionName: calibrationCollectionSelected.value.target_collection_name
    }
    // inform client about debug
    notificationStore.showWarningNotification({
      notification: 'noCalibrationCollection',
      data: data
    })
    activeTab.value = 'calibration'
  }
}
function initTargetCollectionsSelected() {
  targetCollectionsSelected.value = targetsStore.getAllCollections.filter((row) =>
    batchStore.targetCollections
      .map((row) => row.target_collection_id)
      .includes(row.target_collection_id)
  )
  initialTargetCollections.value = targetCollectionsSelected.value
}
function initIonMechanismsSelected() {
  ionMechanismsSelected.value = appStore.ionMechanisms.filter((row) =>
    batchStore.paramIonMechanisms.includes(row.ionization_mechanism_id)
  )
  initialIonizationMechanisms.value = ionMechanismsSelected.value
}
</script>

<template>
  <section>
    <b-modal
      v-model="modalStore.state.sampleBatchOpActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @after-enter="initData"
      @close="modalStore.deactivate"
      :type="action == 'delete' ? 'is-danger' : 'is-primary'"
    >
      <template v-if="['create', 'update', 'editBatchCollections'].includes(action)">
        <div class="modal-card" style="background-color: inherit; height: 800px">
          <header class="modal-card-head">
            <h2 class="subtitle">{{ modalTitle }}</h2>
          </header>
          <section class="modal-card-body" style="min-height: 250px">
            <b-tabs v-model="activeTab" type="is-boxed" position="is-centered" expanded>
              <b-tab-item value="info" label="Info">
                <b-field label="Name">
                  <b-input
                    v-model="batchName"
                    :disabled="action == 'editBatchCollections'"
                    required
                  ></b-input>
                </b-field>
                <b-field label="Description">
                  <b-input
                    v-model="batchDesc"
                    :disabled="action == 'editBatchCollections'"
                  ></b-input>
                </b-field>
              </b-tab-item>
              <b-tab-item
                value="calibration"
                label="Calibration"
                :disabled="calibrationTabDisabled"
              >
                <b-field>
                  <b-select v-model="selectedCalibrationCollectionType" placeholder="Select a type">
                    <option value="targets">Targets collections</option>
                    <option value="calibrants">Calibrants collections</option>
                    <option value="diagnostics">Diagnostic collections</option>
                    <option value="all">All collections</option>
                  </b-select>
                </b-field>
                <b-table
                  :data="displayedCalibrationCollections"
                  :columns="collectionColumns"
                  v-model:selected="calibrationCollectionSelected"
                >
                </b-table>
              </b-tab-item>
              <b-tab-item value="collections" label="Target collections">
                <b-field>
                  <b-select v-model="selectedTargetCollectionType" placeholder="Select a type">
                    <option value="targets">Targets collections</option>
                    <option value="calibrants">Calibrants collections</option>
                    <option value="diagnostics">Diagnostic collections</option>
                    <option value="all">All collections</option>
                  </b-select>
                </b-field>
                <b-table
                  :data="displayedTargetCollections"
                  :columns="collectionColumns"
                  checkable
                  v-model:checked-rows="targetCollectionsSelected"
                >
                </b-table>
              </b-tab-item>
              <b-tab-item
                value="ionization"
                label="Ionization mechanisms"
                :disabled="action == 'editBatchCollections'"
              >
                <b-table
                  :data="appStore.ionMechanisms"
                  :columns="[
                    { field: 'ionization_mechanism', label: 'Mechanism' },
                    {
                      field: 'ionization_mechanism_polarity',
                      label: 'Polarity'
                    }
                  ]"
                  checkable
                  v-model:checked-rows="ionMechanismsSelected"
                >
                </b-table>
              </b-tab-item>
            </b-tabs>
          </section>
          <footer class="modal-card-foot">
            <b-button type="is-dark" icon-left="close" expanded @click="modalStore.deactivate">
              Cancel
            </b-button>
            <b-button
              type="is-primary"
              icon-left="content-save"
              expanded
              :disabled="saveButtonDisabled"
              @click="
                () => {
                  action == 'create'
                    ? batchStore.createBatch(newBatch)
                    : batchStore.updateBatch(newBatch)
                  modalStore.deactivate()
                }
              "
            >
              Save
            </b-button>
          </footer>
        </div>
      </template>
      <template v-if="action == 'delete'">
        <div class="modal-card" style="width: 500px">
          <header class="modal-card-head">
            <h2 class="subtitle">{{ modalTitle }}</h2>
          </header>
          <section class="modal-card-body" style="min-height: 250px">
            <p>Are you sure you want to delete this sample batch?</p>
          </section>
          <footer class="modal-card-foot">
            <b-button type="is-warning" icon-left="close" expanded @click="modalStore.deactivate">
              Cancel
            </b-button>
            <b-button
              type="is-danger"
              icon-left="delete"
              expanded
              @click="
                () => {
                  deleteSampleBatch(batchStore.active)
                  modalStore.deactivate()
                }
              "
            >
              Delete
            </b-button>
          </footer>
        </div>
      </template>
      <template v-if="action == 'copy'">
        <div class="modal-card">
          <!-- style="background-color: inherit; height: 500px" -->
          <header class="modal-card-head">
            <h2 class="subtitle">{{ modalTitle }}</h2>
          </header>
          <section class="modal-card-body">
            <b-field label="New batch name">
              <b-input v-model="newBatchName"></b-input>
            </b-field>
            <b-field label="Description (optional)">
              <b-input v-model="newBatchDescription"></b-input>
            </b-field>

            <!-- Workspace Selection -->
            <b-field label="Select a workspace to copy the batch to:">
              <b-select v-model="workspaceSelected">
                <option :value="sameWorkspace" v-if="sameWorkspace">
                  Same workspace: {{ sameWorkspace.workspace_name }}
                </option>
                <option
                  v-for="workspace in filteredWorkspaces"
                  :key="workspace.workspace_id"
                  :value="workspace"
                >
                  {{ workspace.workspace_name }}
                </option>
              </b-select>
            </b-field>
          </section>
          <footer class="modal-card-foot">
            <b-button type="is-warning" icon-left="close" expanded @click="modalStore.deactivate">
              Cancel
            </b-button>
            <b-button
              type="is-primary"
              icon-left="content-save"
              expanded
              :loading="isCopying"
              :disabled="!newBatchName || !workspaceSelected || isCopying"
              @click="copySampleBatch"
            >
              {{ isCopying ? 'Please Wait...' : 'Copy Batch' }}
            </b-button>
          </footer>
        </div>
      </template>
    </b-modal>
  </section>
</template>
