<script setup>
import * as _ from 'underscore'

import { DialogProgrammatic as dialog } from '@ntohq/buefy-next'

import { ref, computed } from 'vue'

import BaseSpreadsheetInput from '@/components/base/BaseSpreadsheetInput.vue'

import { useAppStore, useModalStore, useTargetsStore, useWorkspaceStore } from '@/stores'

const appStore = useAppStore()
const targetsStore = useTargetsStore()
const modalStore = useModalStore()
const workspaceStore = useWorkspaceStore()

//// Main collection data
// Basic fields
const collectionId = ref('')
const collectionName = ref('')
const collectionDesc = ref('')
const collectionType = ref(null)
// Associations data
const targetCompounds = ref([])
const sampleBatches = ref([])
// Create data
const targetCompoundsCreate = ref([])

//// Utility data
const activeTab = ref(null) // This will hold the value of the active tab
const compoundsTab = ref(null) // This will hold the value of the Target Compounds active subtab
// Select compounds tab
const initialCompounds = ref([]) // To store initial compounds from the active collection
// Pagination properties
const initialCompoundsCurrentPage = ref(1)
const addedCompoundsCurrentPage = ref(1)
const targetCompoundsCreateCurrentPage = ref(1)
// Add compounds tab
const addCompoundsSource = ref(null)
const spreadsheetCompounds = ref([]) // To store pasted to spreadsheet data
const addCompoundsList = ref([]) // To store filtered list of available compounds (already existing in db)
// Pagination properties for addCompoundsList
const addCompoundsCurrentPage = ref(1)
const compoundsPerPage = ref(15)

// Sample Batches tab
const initialBatches = ref([]) // To store initial batches of the active collection
const workspaceSelected = ref(null)
const selectedWorkspaceBatches = ref([]) // Loaded batches of the selected workspace
// Pagination properties for selectedWorkspaceBatches
const selectBatchesCurrentPage = ref(1)
const batchesPerPage = ref(15)

// Delete Modal
const deleteOrphanCompounds = ref(true)

//// General data ////
const action = computed(() => {
  return modalStore.state.targetCollectionOpProps.action
})
const targetCompoundColumns = computed(() => {
  // TODO_target_compound_management make fields editable
  return [
    { field: 'target_compound_name', label: 'Name' },
    { field: 'target_compound_formula', label: 'Formula' },
    { field: 'cas_number', label: 'CAS Number' }
  ]
})
const saveButtonActive = computed(() => {
  switch (action.value) {
    case 'create':
      return (
        !collectionName.value ||
        !collectionType.value ||
        (targetCompounds.value.length === 0 && targetCompoundsCreate.value.length === 0)
      )

    case 'update': {
      // Check if basic properties have changed
      const basicPropertiesChanged =
        collectionName.value !== targetsStore.activeCollection.target_collection_name ||
        collectionDesc.value !== targetsStore.activeCollection.target_collection_description ||
        collectionType.value !== targetsStore.activeCollection.target_collection_type

      // Compare initial and current compounds
      const compoundsChanged =
        !_.isEqual(
          initialCompounds.value.map((compound) => compound.target_compound_id).sort(),
          targetCompounds.value.map((compound) => compound.target_compound_id).sort()
        ) || targetCompoundsCreate.value.length > 0 // Check if there are new compounds to create;

      let disabled = !basicPropertiesChanged && !compoundsChanged

      // Check if there are any compounds to assign or to create
      const hasCompounds =
        targetCompounds.value.length > 0 || targetCompoundsCreate.value.length > 0
      if (!hasCompounds) disabled = true
      return disabled
    }
    case 'manageCollectionBatches':
      return _.isEqual(
        initialBatches.value.map((batch) => batch.sample_batch_id).sort(),
        sampleBatches.value.map((batch) => batch.sample_batch_id).sort()
      )

    default:
      return false
  }
})

//// Labels and titles ////
//// modal
const modalTitle = computed(() => {
  // Define the modal title based on the action
  let title = ''
  switch (action.value) {
    case 'create':
      title = `Create a new target collection ${collectionName.value ?? ''}`
      break
    case 'update':
      title = `Update target collection "${collectionName.value}"`
      break
    case 'manageCollectionBatches':
      title = `Manage batches of "${collectionName.value}" target collection`
      break
    case 'delete':
      title = `Delete target collection "${collectionName.value}"`
      break
  }
  return title
})
//// Target Compounds
// Selected compounds tab
const selectedCompoundsLabel = computed(() => {
  const name = collectionName.value === '' ? 'new' : `"${collectionName.value}"`
  if (
    !initialCompounds.value.length &&
    !addedCompounds.value.length &&
    !targetCompoundsCreate.value.length
  ) {
    return `Please add compounds to the ${name} collection.`
  }
  return `Following checked compounds (uncheck to remove) will be present in the ${name} collection:`
})
const addedCompoundsLabel = computed(() => {
  return `Added compounds:`
})

// Add compounds tab
const addCompoundsListLabel = computed(() => {
  if (addCompoundsSource.value.target_collection_id)
    return 'Select compounds to add from the chosen collection:'
  if (addCompoundsSource.value === 'all') return 'Select compounds to add from all compounds:'
  if (addCompoundsSource.value === 'spreadsheet')
    return 'Select compounds to add from already existing compounds:'
  else return 'Select compounds to add:'
})
const spreadsheetLabel = computed(() => {
  if (addCompoundsSource.value === 'spreadsheet' && spreadsheetCompounds.value.length)
    return 'Pasted target compounds:'
  else return 'Paste a list of target compounds:'
})
// both tabs
const newCompoundsLabel = computed(() => {
  const name = collectionName.value === '' ? 'new' : `"${collectionName.value}"`
  return `Compounds to be created and added to the ${name} collection, please check the name and formula carefully:`
})
//// Sample Batches Tab
const workspaceBatchesSelectionLabel = computed(() => {
  const name = collectionName.value === '' ? 'new' : `"${collectionName.value}"`
  let title = ''
  switch (action.value) {
    case 'create':
    case 'manageCollectionBatches':
      title = `Select batches ${
        workspaceSelected.value
          ? `of the "${this?.workspaceSelected?.workspace_name}" workspace`
          : ''
      } where to add the ${name} collection`
      break
  }
  return title
})
////// tabs data //////
//// Target Compounds Tab ////
// data for Select compounds tab
const paginatedInitialCompounds = computed(() => {
  const start = (initialCompoundsCurrentPage.value - 1) * compoundsPerPage.value
  const end = start + compoundsPerPage.value
  return initialCompounds.value.slice(start, end)
})
const paginatedAddedCompounds = computed(() => {
  const start = (addedCompoundsCurrentPage.value - 1) * compoundsPerPage.value
  const end = start + compoundsPerPage.value
  return addedCompounds.value.slice(start, end)
})
const paginatedTargetCompoundsCreate = computed(() => {
  const start = (targetCompoundsCreateCurrentPage.value - 1) * compoundsPerPage.value
  const end = start + compoundsPerPage.value
  return targetCompoundsCreate.value.slice(start, end)
})
// Computes the added compounds by filtering out those that are not in the initial compounds
const addedCompounds = computed(() => {
  return targetCompounds.value.filter(
    (compound) =>
      !initialCompounds.value.some(
        (initialCompound) => initialCompound.target_compound_id === compound.target_compound_id
      )
  )
})

// data for Add compounds tab
const filteredCollections = computed(() => {
  if (action.value !== 'create') {
    return targetsStore.getAllCollections.filter((collection) => {
      return collection.target_collection_id !== targetsStore.activeCollection.target_collection_id
    })
  }
  return targetsStore.getAllCollections
})

const paginatedAddCompoundsList = computed(() => {
  const start = (addCompoundsCurrentPage.value - 1) * compoundsPerPage.value
  const end = start + compoundsPerPage.value
  return addCompoundsList.value.slice(start, end)
})

/// Sample Batches Tab ////
// Select workspaces
const currentWorkspace = computed(() => {
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
const paginatedSelectedWorkspaceBatches = computed(() => {
  const start = (selectBatchesCurrentPage.value - 1) * batchesPerPage.value
  const end = start + batchesPerPage.value
  return selectedWorkspaceBatches.value.slice(start, end)
})

//// data to form http request ////
const targetCompoundsIds = computed(() => {
  return targetCompounds.value.map((compound) => compound.target_compound_id)
})
const sampleBatchesIds = computed(() => {
  return sampleBatches.value.map((batch) => batch.sample_batch_id)
})
const newCollection = computed(() => {
  if (actionIs.value('create')) {
    return {
      target_collection_name: collectionName.value,
      target_collection_description: collectionDesc.value,
      target_collection_type: collectionType.value,
      target_compound_ids: targetCompoundsIds.value,
      target_compounds_create: targetCompoundsCreate.value,
      sample_batch_ids: sampleBatchesIds.value
    }
  }
  if (actionIs.value('update')) {
    return {
      target_collection_id: targetsStore.activeCollection.target_collection_id,
      target_collection_name: collectionName.value,
      target_collection_description: collectionDesc.value,
      target_collection_type: collectionType.value,
      target_compound_ids: targetCompoundsIds.value,
      target_compounds_create: targetCompoundsCreate.value
    }
  }
  if (actionIs.value('manageCollectionBatches')) {
    return {
      target_collection_id: targetsStore.activeCollection.target_collection_id,
      target_collection_name: collectionName.value,
      target_collection_description: collectionDesc.value,
      target_collection_type: collectionType.value,
      sample_batch_ids: sampleBatchesIds.value
    }
  }
  return null
})

//// General methods ////
function actionIs(...actions) {
  return actions.includes(modalStore.state.targetCollectionOpProps.action)
}
function deactivateModalResetData() {
  modalStore.deactivate()
  resetData()
}
function deleteButtonClick() {
  dialog.confirm({
    message: `Are you sure you want to delete '${collectionName.value}' target collection?`,
    confirmText: 'Delete',
    type: 'is-danger',
    hasIcon: true,
    icon: 'delete-alert',
    onConfirm: async () => {
      targetsStore.deleteCollection({
        collectionId: collectionId.value,
        collectionName: collectionName.value,
        deleteOrphanCompounds: deleteOrphanCompounds.value
      })
      deactivateModalResetData()
    }
  })
}
//// Data loading ////
// General data loading methods
// Initialization logic when the modal is activated
function initData() {
  // Initializes data specific to the 'create' action
  if (action.value == 'create') {
    activeTab.value = 'info'
    compoundsTab.value = 'addCompounds'
    collectionId.value = ''
    collectionName.value = ''
    collectionDesc.value = ''
    collectionType.value = null
    targetCompounds.value = []
    initialCompounds.value = targetCompounds.value
    targetCompoundsCreate.value = []
    spreadsheetCompounds.value = []
    sampleBatches.value = []
    initialBatches.value = sampleBatches.value
    workspaceSelected.value = currentWorkspace.value ?? null
    if (workspaceStore.activeBatches) reconcileBatches(workspaceStore.activeBatches)
  }
  // Initializes data specific to the 'update' action
  if (this.actionIs('update')) {
    activeTab.value = 'info'
    compoundsTab.value = 'selectedCompounds'
    // Reset the selected compounds tab to the first page when the list is reloaded
    initialCompoundsCurrentPage.value = 1
    collectionId.value = targetsStore.activeCollection.value?.target_collection_id ?? ''
    collectionName.value = targetsStore.activeCollection.value?.target_collection_name ?? ''
    collectionDesc.value = targetsStore.activeCollection.value?.target_collection_description ?? ''
    collectionType.value = targetsStore.activeCollection.value?.target_collection_type ?? null
    targetCompounds.value = targetsStore.activeCollection.value?.target_compounds ?? []
    initialCompounds.value = targetCompounds.value
    targetCompoundsCreate.value = []
    spreadsheetCompounds.value = []
  }
  // Initializes data specific to the 'manageCollectionBatches' action
  if (action.value == 'manageCollectionBatches') {
    activeTab.value = 'batches'
    collectionId.value = targetsStore.activeCollection.value?.target_collection_id ?? ''
    collectionName.value = targetsStore.activeCollection.value?.target_collection_name ?? ''
    collectionDesc.value = targetsStore.activeCollection.value?.target_collection_description ?? ''
    collectionType.value = targetsStore.activeCollection.value?.target_collection_type ?? null
    sampleBatches.value = targetsStore.activeCollection.value?.sample_batches ?? []
    initialBatches.value = sampleBatches.value
    workspaceSelected.value = currentWorkspace.value ?? null
    if (workspaceStore.activeBatches) reconcileBatches.value(workspaceStore.activeBatches)
  }
  // Initializes data specific to the 'delete' action
  if (action.value == 'delete') {
    collectionId.value = targetsStore.activeCollection?.target_collection_id ?? ''
    collectionName.value = targetsStore.activeCollection?.target_collection_name ?? ''
    deleteOrphanCompounds.value = true
  }
}
function resetData() {
  modalStore.state.targetCollectionOpProps = {}
  activeTab.value = 'info'
  compoundsTab.value = 'selectedCompounds'
  collectionId.value = ''
  collectionName.value = ''
  collectionDesc.value = ''
  collectionType.value = null
  targetCompounds.value = []
  targetCompoundsCreate.value = []
  sampleBatches.value = []
  addCompoundsSource.value = null
  addCompoundsList.value = []
  spreadsheetCompounds.value = []
  workspaceSelected.value = null
  selectedWorkspaceBatches.value = []
  deleteOrphanCompounds.value = true
  addedCompoundsCurrentPage.value = 1
  targetCompoundsCreateCurrentPage.value = 1
}
// Data loading methods for Add compounds tab
async function loadAddCompoundsList() {
  if (!addCompoundsSource.value) return
  if (addCompoundsSource.value === 'spreadsheet') {
    addCompoundsList.value = []
    return
  }
  // Reset add compounds list to the first page when the list is reloaded
  addCompoundsCurrentPage.value = 1

  let compoundsToProcess = []
  if (addCompoundsSource.value === 'all') {
    compoundsToProcess = targetsStore.getAllCompounds
  }
  if (addCompoundsSource.value.target_collection_id) {
    const collectionId = addCompoundsSource.value.target_collection_id
    const collection = await targetsStore.getTargetCollection(collectionId)
    compoundsToProcess = collection?.target_compounds || []
  }
  // check if the loaded collection has any compounds
  if (!compoundsToProcess.length) return
  reconcileCompounds(compoundsToProcess)
}

// Reconcile compounds to maintain reference equality with compounds in targetCompounds and initialCompounds list.
function reconcileCompounds(compounds) {
  // Combine initialCompounds and targetCompounds to cover all compounds that are already part of the collection or selected
  const combinedCompounds = [...initialCompounds.value, ...targetCompounds.value]

  // Use a Map to eliminate duplicate compounds based on a unique identifier (target_compound_id or formula)
  const compoundMap = new Map(
    combinedCompounds.map((compound) => [
      compound.target_compound_id || compound.target_compound_formula,
      compound
    ])
  )

  this.addCompoundsList = compounds.map((compound) => {
    // First, try finding by target_compound_id, if not found by ID and there's no ID on the new compound, try finding by formula
    let selectedCompound = compoundMap.get(
      compound.target_compound_id || compound.target_compound_formula
    )

    // If found, use the existing compound from combinedCompounds if available; otherwise, use the current compound
    return selectedCompound || compound
  })
}

// spreadsheet loading
async function loadSpreadsheetCompounds(rows) {
  if (addCompoundsSource.value !== 'spreadsheet') return
  // Reset add compounds list to the first page when the list is reloaded
  addCompoundsCurrentPage.value = 1
  targetCompoundsCreateCurrentPage.value = 1
  targetCompoundsCreate.value = []
  spreadsheetCompounds.value = rows
  const { existingCompounds, notExistingCompounds } =
    await targetsStore.processSpreadsheetInput(rows)

  // Reconcile existing compounds
  reconcileCompounds.value(existingCompounds)

  // Add notExistingCompounds to a list for creation
  targetCompoundsCreate.value.push(...notExistingCompounds)
}

// Data loading methods for Sample Batches tab
function reconcileBatches(batches) {
  selectedWorkspaceBatches.value = batches.map((batch) => {
    // Try to find an existing batch in sampleBatches
    const existingBatch = this.sampleBatches.find(
      (sb) => sb.sample_batch_id === batch.sample_batch_id
    )
    // If found, use the existing batch object to maintain reference equality; otherwise, use the current batch
    return existingBatch || batch
  })
}

async function loadWorkspaceBatches() {
  if (!workspaceSelected.value) return

  // Reset to the first page when the list is reloaded
  selectBatchesCurrentPage.value = 1

  const workspaceBatches = await workspaceStore.getWorkspaceBatches(
    workspaceSelected.value.workspace_id
  )
  if (!workspaceBatches.length) return
  // Reconcile the loaded batches with those already present in sampleBatches
  reconcileBatches(workspaceBatches)
}
</script>

<template>
  <section>
    <b-modal
      v-model="modalStore.state.targetCollectionOpActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @after-enter="initData"
      @close="deactivateModalResetData"
      :type="actionIs('delete') ? 'is-danger' : 'is-primary'"
    >
      <template v-if="actionIs('create', 'update', 'manageCollectionBatches')">
        <div class="modal-card" style="background-color: inherit; height: 90vh">
          <header class="modal-card-head">
            <p class="subtitle">{{ modalTitle }}</p>
          </header>
          <section class="modal-card-body" style="min-height: 250px">
            <b-tabs v-model="activeTab" type="is-boxed" position="is-centered" expanded>
              <!-- Basic fields -->
              <b-tab-item value="info" label="Info">
                <b-field label="Name">
                  <b-input
                    v-model="collectionName"
                    placeholder="Enter a name for the target collection"
                    :disabled="action == 'manageCollectionBatches'"
                    required
                  ></b-input>
                </b-field>
                <b-field label="Description">
                  <b-input
                    v-model="collectionDesc"
                    placeholder="Enter a description for the target collection"
                    :disabled="action == 'manageCollectionBatches'"
                  ></b-input>
                </b-field>
                <b-field label="Collection type">
                  <b-dropdown
                    aria-role="list"
                    v-model="collectionType"
                    :disabled="action == 'manageCollectionBatches'"
                    expanded
                  >
                    <template #trigger>
                      <b-button
                        :label="collectionType || 'Select Type'"
                        icon-right="menu-down"
                        expanded
                        style="align: left"
                      />
                    </template>
                    <b-dropdown-item
                      aria-role="listitem"
                      v-for="collectionType in collectionTypes"
                      :key="collectionType"
                      :value="collectionType"
                    >
                      {{ collectionType }}
                    </b-dropdown-item>
                  </b-dropdown>
                </b-field>
              </b-tab-item>

              <!-- Target compounds associations -->
              <b-tab-item
                value="compounds"
                label="Target compounds"
                :disabled="action == 'manageCollectionBatches'"
              >
                <b-tabs type="is-toggle" v-model="compoundsTab" expanded>
                  <!-- Selected compounds tab -->
                  <b-tab-item value="selectedCompounds" label="Selected compounds">
                    <b-field :label="selectedCompoundsLabel"></b-field>
                    <b-field
                      v-if="initialCompounds.length > 0"
                      :label="`Current compounds of '${collectionName}'`"
                    >
                      <b-table
                        :data="paginatedInitialCompounds"
                        :columns="targetCompoundColumns"
                        checkable
                        v-model:checked-rows="targetCompounds"
                        paginated
                      >
                        <!-- Optional: Pagination controls -->
                        <template v-slot:pagination>
                          <b-pagination
                            :total="initialCompounds.length"
                            v-model:current="initialCompoundsCurrentPage"
                            :per-page="compoundsPerPage"
                            size="is-small"
                          ></b-pagination>
                        </template>
                      </b-table>
                    </b-field>
                    <b-field :label="addedCompoundsLabel" v-if="addedCompounds.length > 0">
                      <b-table
                        :data="paginatedAddedCompounds"
                        :columns="targetCompoundColumns"
                        checkable
                        v-model:checked-rows="targetCompounds"
                        paginated
                      >
                        <!-- Optional: Pagination controls -->
                        <template v-slot:pagination>
                          <b-pagination
                            :total="addedCompounds.length"
                            v-model:current="addedCompoundsCurrentPage"
                            :per-page="compoundsPerPage"
                            size="is-small"
                          ></b-pagination>
                        </template>
                      </b-table>
                    </b-field>
                    <b-field :label="newCompoundsLabel" v-if="targetCompoundsCreate.length > 0">
                      <b-table
                        :data="paginatedTargetCompoundsCreate"
                        :columns="targetCompoundColumns"
                        checkable
                        v-model:checked-rows="targetCompoundsCreate"
                        paginated
                      >
                        <!-- Optional: Pagination controls -->
                        <template v-slot:pagination>
                          <b-pagination
                            :total="targetCompoundsCreate.length"
                            v-model:current="targetCompoundsCreateCurrentPage"
                            :per-page="compoundsPerPage"
                            size="is-small"
                          ></b-pagination>
                        </template>
                      </b-table>
                    </b-field>
                  </b-tab-item>
                  <!-- Add compounds tab -->
                  <b-tab-item value="addCompounds" label="Add compounds">
                    <!-- Source Selection -->
                    <b-field label="Add target compounds from">
                      <b-select
                        v-model="addCompoundsSource"
                        @input="loadAddCompoundsList"
                        placeholder="Select a source for adding compounds"
                        expanded
                      >
                        <optgroup label="Target Collections">
                          <option
                            v-for="collection in filteredCollections"
                            :key="collection.target_collection_id"
                            :value="collection"
                          >
                            {{ collection.target_collection_name }}
                          </option>
                        </optgroup>
                        <option value="all">All compounds</option>
                        <option value="spreadsheet">Spreadsheet</option>
                      </b-select>
                    </b-field>

                    <!-- Spreadsheet compounds input -->
                    <b-field v-if="addCompoundsSource === 'spreadsheet'">
                      <base-spreadsheet-input
                        :label="spreadsheetLabel"
                        :cols="targetCompoundColumns"
                        @rowsPasted="loadSpreadsheetCompounds"
                      ></base-spreadsheet-input>
                    </b-field>

                    <!-- Add Compounds Selection -->
                    <b-field :label="addCompoundsListLabel" v-if="addCompoundsList.length > 0">
                      <b-table
                        :data="paginatedAddCompoundsList"
                        :columns="targetCompoundColumns"
                        checkable
                        v-model:checked-rows="targetCompounds"
                        paginated
                      >
                        <!-- Optional: Pagination controls -->
                        <template v-slot:pagination>
                          <b-pagination
                            :total="addCompoundsList.length"
                            v-model:current="addCompoundsCurrentPage"
                            :per-page="compoundsPerPage"
                            size="is-small"
                          ></b-pagination>
                        </template>
                      </b-table>
                    </b-field>
                    <b-field :label="newCompoundsLabel" v-if="targetCompoundsCreate.length > 0">
                      <b-table
                        :data="paginatedTargetCompoundsCreate"
                        :columns="targetCompoundColumns"
                        checkable
                        v-model:checked-rows="targetCompoundsCreate"
                        paginated
                      >
                        <!-- Optional: Pagination controls -->
                        <template v-slot:pagination>
                          <b-pagination
                            :total="targetCompoundsCreate.length"
                            v-model:current="targetCompoundsCreateCurrentPage"
                            :per-page="compoundsPerPage"
                            size="is-small"
                          ></b-pagination>
                        </template>
                      </b-table>
                    </b-field>
                  </b-tab-item>
                </b-tabs>
              </b-tab-item>

              <!-- Sample batches associations -->
              <b-tab-item value="batches" label="Sample batches" :disabled="action == 'update'">
                <!-- Source Selection -->
                <b-field label="Choose a workspace">
                  <b-select
                    v-model="workspaceSelected"
                    @input="loadWorkspaceBatches"
                    placeholder="Choose a workspace"
                    expanded
                  >
                    <option :value="currentWorkspace" v-if="currentWorkspace">
                      Current workspace: {{ currentWorkspace.workspace_name }}
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
                <!-- Workspace Batches Selection -->
                <b-field :label="workspaceBatchesSelectionLabel">
                  <b-table
                    :data="paginatedSelectedWorkspaceBatches"
                    :columns="[{ field: 'sample_batch_name', label: 'Batch' }]"
                    checkable
                    v-model:checked-rows="sampleBatches"
                    paginated
                  >
                    <!-- Optional: Pagination controls -->
                    <template v-slot:pagination>
                      <b-pagination
                        :total="selectedWorkspaceBatches.length"
                        v-model:current="selectBatchesCurrentPage"
                        :per-page="batchesPerPage"
                        size="is-small"
                      ></b-pagination>
                    </template>
                  </b-table>
                </b-field>
              </b-tab-item>
            </b-tabs>
          </section>
          <footer class="modal-card-foot">
            <b-button type="is-dark" icon-left="close" expanded @click="deactivateModalResetData">
              Cancel
            </b-button>
            <b-button
              type="is-primary"
              icon-left="content-save"
              expanded
              :disabled="saveButtonActive"
              @click="
                () => {
                  actionIs('create')
                    ? targetsStore.createCollection(newCollection)
                    : targetsStore.updateCollection(newCollection)
                  deactivateModalResetData()
                }
              "
            >
              Save
            </b-button>
          </footer>
        </div>
      </template>
      <template v-else-if="actionIs('delete')">
        <div class="modal-card" style="height: 28vh">
          <header class="modal-card-head">
            <p class="subtitle">{{ modalTitle }}</p>
          </header>
          <section
            class="modal-card-body"
            style="
              min-height: 150px;
              display: flex;
              flex-direction: column;
              justify-content: center;
            "
          >
            <b-field
              :label="`Would you like to keep or remove compounds from '${collectionName}' that are not part of any other collection?`"
            >
            </b-field>
            <b-field>
              <b-radio v-model="deleteOrphanCompounds" :native-value="false" type="is-info">
                Delete the collection and keep the unique compounds
              </b-radio>
            </b-field>
            <b-field>
              <b-radio v-model="deleteOrphanCompounds" :native-value="true" type="is-primary">
                Delete the collection and its unique compounds
              </b-radio>
            </b-field>
          </section>
          <footer class="modal-card-foot">
            <b-button type="is-dark" icon-left="close" expanded @click="deactivateModalResetData">
              Cancel
            </b-button>
            <b-button type="is-danger" icon-left="delete" expanded @click="deleteButtonClick">
              Delete
            </b-button>
          </footer>
        </div>
      </template>
    </b-modal>
  </section>
</template>

<style scoped>
optgroup {
  color: #464752 !important;
}
</style>
