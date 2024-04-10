<script setup>
import { ref, computed, watch } from 'vue'

import BaseSpreadsheetInput from '@/components/base/BaseSpreadsheetInput.vue'

import { dialog } from '@/main'
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
// Add compounds tab
const addCompoundsSource = ref(null)
const spreadsheetCompounds = ref([]) // To store pasted to spreadsheet data
const addCompoundsList = ref([]) // To store filtered list of available compounds (already existing in db)

// Sample Batches tab
const initialBatches = ref([]) // To store initial batches of the active collection
const workspaceSelected = ref(null)
const selectedWorkspaceBatches = ref([]) // Loaded batches of the selected workspace

// Delete Modal
const deleteOrphanCompounds = ref(true)

//// General data ////
const action = computed(() => modalStore.state.targetCollectionOpProps.action)
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
        !(
          initialCompounds.value
            .map((compound) => compound.target_compound_id)
            .sort()
            .join() ==
          targetCompounds.value
            .map((compound) => compound.target_compound_id)
            .sort()
            .join()
        ) || targetCompoundsCreate.value.length > 0 // Check if there are new compounds to create;

      let disabled = !basicPropertiesChanged && !compoundsChanged

      // Check if there are any compounds to assign or to create
      const hasCompounds =
        targetCompounds.value.length > 0 || targetCompoundsCreate.value.length > 0
      if (!hasCompounds) disabled = true
      return disabled
    }
    case 'manageCollectionBatches':
      return (
        initialBatches.value
          .map((batch) => batch.sample_batch_id)
          .sort()
          .join() ==
        sampleBatches.value
          .map((batch) => batch.sample_batch_id)
          .sort()
          .join()
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
          ? `of the "${workspaceSelected.value?.workspace_name}" workspace`
          : ''
      } where to add the ${name} collection`
      break
  }
  return title
})
////// tabs data //////
//// Target Compounds Tab ////
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

//// data to form http request ////
const targetCompoundsIds = computed(() => {
  return targetCompounds.value.map((compound) => compound.target_compound_id)
})
const sampleBatchesIds = computed(() => {
  return sampleBatches.value.map((batch) => batch.sample_batch_id)
})
const newCollection = computed(() => {
  if (action.value == 'create') {
    return {
      target_collection_name: collectionName.value,
      target_collection_description: collectionDesc.value,
      target_collection_type: collectionType.value,
      target_compound_ids: targetCompoundsIds.value,
      target_compounds_create: targetCompoundsCreate.value,
      sample_batch_ids: sampleBatchesIds.value
    }
  }
  if (action.value == 'update') {
    return {
      target_collection_id: targetsStore.activeCollection.target_collection_id,
      target_collection_name: collectionName.value,
      target_collection_description: collectionDesc.value,
      target_collection_type: collectionType.value,
      target_compound_ids: targetCompoundsIds.value,
      target_compounds_create: targetCompoundsCreate.value
    }
  }
  if (action.value == 'manageCollectionBatches') {
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
  if (action.value == 'update') {
    activeTab.value = 'info'
    compoundsTab.value = 'selectedCompounds'
    // Reset the selected compounds tab to the first page when the list is reloaded
    collectionId.value = targetsStore.activeCollection?.target_collection_id ?? ''
    collectionName.value = targetsStore.activeCollection?.target_collection_name ?? ''
    collectionDesc.value = targetsStore.activeCollection?.target_collection_description ?? ''
    collectionType.value = targetsStore.activeCollection?.target_collection_type ?? null
    targetCompounds.value = targetsStore.activeCollection?.target_compounds ?? []
    initialCompounds.value = targetCompounds.value
    targetCompoundsCreate.value = []
    spreadsheetCompounds.value = []
  }
  // Initializes data specific to the 'manageCollectionBatches' action
  if (action.value == 'manageCollectionBatches') {
    activeTab.value = 'batches'
    collectionId.value = targetsStore.activeCollection?.target_collection_id ?? ''
    collectionName.value = targetsStore.activeCollection?.target_collection_name ?? ''
    collectionDesc.value = targetsStore.activeCollection?.target_collection_description ?? ''
    collectionType.value = targetsStore.activeCollection?.target_collection_type ?? null
    sampleBatches.value = targetsStore.activeCollection?.sample_batches ?? []
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
  loadWorkspaceBatches()
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
}
// Data loading methods for Add compounds tab
async function loadAddCompoundsList() {
  if (!addCompoundsSource.value) return
  if (addCompoundsSource.value === 'spreadsheet') {
    addCompoundsList.value = []
    return
  }

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

watch(addCompoundsSource, loadAddCompoundsList)

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

  addCompoundsList.value = compounds.map((compound) => {
    // First, try finding by target_compound_id, if not found by ID and there's no ID on the new compound, try finding by formula
    let selectedCompound = compoundMap.get(
      compound.target_compound_id || compound.target_compound_formula
    )

    // If found, use the existing compound from combinedCompounds if available; otherwise, use the current compound
    return selectedCompound ?? compound
  })
}

// spreadsheet loading
async function loadSpreadsheetCompounds(rows) {
  console.log(rows)
  if (addCompoundsSource.value !== 'spreadsheet') return
  // Reset add compounds list to the first page when the list is reloaded
  targetCompoundsCreate.value = []
  spreadsheetCompounds.value = rows
  const { existingCompounds, notExistingCompounds } =
    await targetsStore.processSpreadsheetInput(rows)

  // Reconcile existing compounds
  reconcileCompounds(existingCompounds)

  // Add notExistingCompounds to a list for creation
  targetCompoundsCreate.value.push(...notExistingCompounds)
}

// Data loading methods for Sample Batches tab
function reconcileBatches(batches) {
  selectedWorkspaceBatches.value = batches.map((batch) => {
    // Try to find an existing batch in sampleBatches
    const existingBatch = sampleBatches.value.find(
      (sb) => sb.sample_batch_id === batch.sample_batch_id
    )
    // If found, use the existing batch object to maintain reference equality; otherwise, use the current batch
    return existingBatch ?? batch
  })
}

async function loadWorkspaceBatches() {
  if (!workspaceSelected.value) return

  const workspaceBatches = await workspaceStore.getWorkspaceBatches(
    workspaceSelected.value.workspace_id
  )
  // Reconcile the loaded batches with those already present in sampleBatches
  reconcileBatches(workspaceBatches)
}

watch(workspaceSelected, loadWorkspaceBatches)
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
      :type="action == 'delete' ? 'is-danger' : 'is-primary'"
    >
      <template v-if="['create', 'update', 'manageCollectionBatches'].includes(action)">
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
                      v-for="collectionType in targetsStore.collectionTypes"
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
                        :data="initialCompounds"
                        :columns="targetCompoundColumns"
                        checkable
                        v-model:checked-rows="targetCompounds"
                      />
                    </b-field>
                    <b-field :label="addedCompoundsLabel" v-if="addedCompounds.length > 0">
                      <b-table
                        :data="addedCompounds"
                        :columns="targetCompoundColumns"
                        checkable
                        v-model:checked-rows="targetCompounds"
                      />
                    </b-field>
                    <b-field :label="newCompoundsLabel" v-if="targetCompoundsCreate.length > 0">
                      <b-table
                        :data="targetCompoundsCreate"
                        :columns="targetCompoundColumns"
                        checkable
                        v-model:checked-rows="targetCompoundsCreate"
                      />
                    </b-field>
                  </b-tab-item>
                  <!-- Add compounds tab -->
                  <b-tab-item value="addCompounds" label="Add compounds">
                    <!-- Source Selection -->
                    <b-field label="Add target compounds from">
                      <b-select
                        v-model="addCompoundsSource"
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
                        :data="addCompoundsList"
                        :columns="targetCompoundColumns"
                        checkable
                        v-model:checked-rows="targetCompounds"
                      />
                    </b-field>
                    <b-field :label="newCompoundsLabel" v-if="targetCompoundsCreate.length > 0">
                      <b-table
                        :data="targetCompoundsCreate"
                        :columns="targetCompoundColumns"
                        checkable
                        v-model:checked-rows="targetCompoundsCreate"
                      />
                    </b-field>
                  </b-tab-item>
                </b-tabs>
              </b-tab-item>

              <!-- Sample batches associations -->
              <b-tab-item value="batches" label="Sample batches" :disabled="action == 'update'">
                <!-- Source Selection -->
                <b-field label="Choose a workspace">
                  <b-select v-model="workspaceSelected" placeholder="Choose a workspace" expanded>
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
                    :data="selectedWorkspaceBatches"
                    :columns="[{ field: 'sample_batch_name', label: 'Batch' }]"
                    checkable
                    v-model:checked-rows="sampleBatches"
                  />
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
                  action == 'create'
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
      <template v-else-if="action == 'delete'">
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
