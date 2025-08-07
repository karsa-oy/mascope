<script setup>
import { ref, reactive, computed, watch, watchEffect, onMounted, onBeforeUnmount } from 'vue'

import Dialog from 'primevue/dialog'
import FloatLabel from 'primevue/floatlabel'
import SelectButton from 'primevue/selectbutton'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import RadioButton from 'primevue/radiobutton'
import InputText from 'primevue/inputtext'
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InlineMessage from 'primevue/inlinemessage'
import Listbox from 'primevue/listbox'
import Select from 'primevue/select'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import { useConfirm } from 'primevue/useconfirm'

import { api } from '@/api'
import { useApp } from '@/stores'
import { fromSpreadsheet, equals } from '@/lib/table'
import { BaseClipboardContext } from '@/lib/base'
import { isValidChemicalFormula, findExistingCompound } from '@/lib/chem'
import { clone } from '@/lib/utils'
import { collectionTypes, getAllowedWorkspaceTypes, getAllowedBatchTypes } from '@/lib/constants'

const confirm = useConfirm()

const app = useApp()

const action = defineModel('action')

const props = defineProps({
  collection: {
    type: Object
  }
})
const original = computed(() => props.collection ?? app.data.target.collection.focused)

// dialog visibility reactivity
const visible = ref(false)
watch(action, (value) => {
  visible.value = !!value
})
watch(visible, (value) => {
  if (!value) {
    action.value = null
  }
})

const info = reactive({
  id: null,
  name: '',
  desc: '',
  type: 'TARGETS'
})
const compounds = reactive({
  loaded: [],
  selected: [],
  initial: [],
  created: [],
  deleted: []
})
const batches = reactive({
  loaded: [],
  selected: [],
  initial: []
})
const selected = reactive({
  workspace: null,
  source: 'collection',
  collection: 'all-compounds', // for adding compounds
  search: '',
  tab: 'compounds',
  all: {
    targets: false,
    batches: false
  }
})
const add = reactive({
  expanded: false,
  formula: null,
  name: null,
  cas: null
})
const deleteOrphans = ref(true)

const key = reactive({
  targets: 0,
  batches: 0
})

const columns = [
  { field: 'target_compound_name', label: 'Name' },
  { field: 'target_compound_formula', label: 'Formula' },
  { field: 'cas_number', label: 'CAS' },
  { field: 'status', label: 'Status' }
]

const batchLabel = computed(() =>
  batches.selected.length == 1
    ? `"${batches.selected[0].sample_batch_name}" batch`
    : `${batches.selected.length} batches`
)

const title = computed(() => {
  // Define the modal title based on the action
  let title = ''
  switch (action.value) {
    case 'create':
      title = 'Create a new target collection'
      break
    case 'update':
      title = 'Edit target collection'
      break
    case 'update_batches':
      title = 'Manage target collection batches'
      break
    case 'delete':
      title = 'Delete target collection'
      break
  }
  return title
})

const changes = computed(() =>
  [
    ...compounds.selected,
    ...compounds.created,
    ...compounds.initial.filter(
      (initial) =>
        !compounds.selected.find(
          (selected) => selected.target_compound_id == initial.target_compound_id
        )
    )
  ].map((comp) => {
    const selected = compounds.selected.some(
      (selected) => selected.target_compound_id == comp.target_compound_id
    )
    const prexisting = compounds.initial.some(
      (init) => init.target_compound_id == comp.target_compound_id
    )
    const created = compounds.created.some(
      (created) => created.target_compound_formula == comp.target_compound_formula
    )
    const added = comp.target_compound_id && !prexisting
    const removed = prexisting && !selected
    let status
    if (created) {
      status = '1 create'
    }
    if (selected) {
      if (added) {
        status = '2 add'
      } else if (prexisting) {
        status = '3 keep'
      }
    } else {
      if (removed) {
        status = '4 remove'
      }
    }
    return {
      ...comp,
      status
    }
  })
)

const filteredWorkspaces = computed(() => {
  if (!info.type) return app.data.workspace.list

  const allowedWorkspaceTypes = getAllowedWorkspaceTypes(info.type)
  return app.data.workspace.list
    .filter((workspace) => allowedWorkspaceTypes.includes(workspace.workspace_type))
    .sort((a, b) => {
      // ensure the current workspace comes first if it's allowed
      if (a.workspace_id == app.data.workspace.focusedId) return -1
      if (b.workspace_id == app.data.workspace.focusedId) return 1
      return 0
    })
    .map((workspace, index) => ({
      // create labels, demarcating the current one
      ...workspace,
      label: index > 0 ? workspace.workspace_name : `${workspace.workspace_name} (current)`
    }))
})

function remove(compound) {
  if (compound.status == '1 create') {
    compounds.created = compounds.created.filter(
      (selected) =>
        !findExistingCompound([selected], {
          target_compound_formula: compound.target_compound_formula,
          target_compound_name: compound.target_compound_name,
          cas_number: compound.cas_number
        })
    )
  } else {
    compounds.selected = compounds.selected.filter(
      (selected) =>
        !findExistingCompound([selected], {
          target_compound_formula: compound.target_compound_formula,
          target_compound_name: compound.target_compound_name,
          cas_number: compound.cas_number
        })
    )
  }
}
function restore(compound) {
  compounds.selected.push(compound)
}

watchEffect(() => {
  if (selected.source == 'input') {
    selected.search = ''
  }
})
watchEffect(async () => {
  // reload compounds
  compounds.loaded =
    selected.collection === 'all-compounds'
      ? app.data.target.compound.list
      : ((await app.data.target.collection.read(selected.collection))?.target_compounds ?? [])
  // select all checkbox state
  selected.all.targets =
    compounds.loaded.length > 0
      ? compounds.loaded.every((comp) =>
          compounds.selected
            .map(({ target_compound_id }) => target_compound_id)
            .includes(comp.target_compound_id)
        )
      : false
})
function loadSpreadsheet({ rows }) {
  let prexisting = []
  rows.forEach((compound) => {
    const record = findExistingCompound(app.data.target.compound.list, compound)
    if (record) {
      prexisting.push(record)
    } else {
      const created = compounds.created.find(
        ({ target_compound_formula }) => target_compound_formula == compound.target_compound_formula
      )
      if (!created) {
        compounds.created.push(compound)
      }
    }
  })
  const index = new Map(
    [...compounds.selected, ...prexisting].map((compound) => [
      compound.target_compound_id ?? compound.target_compound_formula,
      compound
    ])
  )
  // reconcile with exisiting compounds
  const reconciled = prexisting.map(
    (compound) =>
      index.get(compound.target_compound_id ?? compound.target_compound_formula) ?? compound
  )
  const unselected = (added) =>
    !findExistingCompound(compounds.selected, {
      target_compound_formula: added.target_compound_formula,
      target_compound_name: added.target_compound_name,
      cas_number: added.cas_number
    })
  compounds.selected.push(...reconciled.filter(unselected))
}

watchEffect(() => loadBatches(selected.workspace, info.type))

async function loadBatches(workspace, collectionType) {
  if (!workspace || !collectionType) {
    batches.loaded = []
    return
  }
  const allowedBatchTypes = getAllowedBatchTypes(collectionType)

  const latest = await api.http.get(`/sample/batches`, {
    params: {
      workspace_id: workspace.workspace_id,
      sample_batch_type: allowedBatchTypes
    },
    use: 'read',
    type: 'load_batches'
  })
  // reconcile with existing data
  batches.loaded = latest.map(
    (batch) =>
      batches.loaded.find(({ sample_batch_id }) => sample_batch_id === batch.sample_batch_id) ??
      batch
  )
  // select all checkbox state
  selected.all.batches =
    batches.loaded.length > 0
      ? batches.loaded.every((batch) =>
          batches.selected
            .map(({ sample_batch_id }) => sample_batch_id)
            .includes(batch.sample_batch_id)
        )
      : false
}

// watcher to reset batch selections when collection type changes
watch(
  () => info.type,
  (newType, oldType) => {
    if (oldType && newType !== oldType) {
      // Reset workspace if it becomes invalid
      if (selected.workspace) {
        const allowedWorkspaceTypes = getAllowedWorkspaceTypes(newType)
        if (!allowedWorkspaceTypes.includes(selected.workspace.workspace_type)) {
          selected.workspace = null
        }
      }

      // Reset batch selections if they become invalid
      if (batches.selected.length > 0) {
        const allowedBatchTypes = getAllowedBatchTypes(newType)
        batches.selected = batches.selected.filter((batch) =>
          allowedBatchTypes.includes(batch.sample_batch_type)
        )
      }
    }
  }
)

function execute() {
  const common = {
    target_collection_name: info.name,
    target_collection_description: info.desc,
    target_collection_type: info.type
  }
  const target_collection_id = original.value?.target_collection_id
  const target_compound_ids =
    compounds.selected?.map(({ target_compound_id }) => target_compound_id) ?? []
  const sample_batch_ids = batches.selected.map(({ sample_batch_id }) => sample_batch_id)
  const target_compounds_create = compounds.created

  switch (action.value) {
    case 'create': {
      app.data.target.collection.create({
        ...common,
        target_compound_ids,
        sample_batch_ids,
        target_compounds_create
      })
      break
    }
    case 'update': {
      app.data.target.collection.update({
        ...common,
        target_collection_id,
        target_compound_ids,
        target_compounds_create
      })
      break
    }
    case 'update_batches': {
      app.data.target.collection.update({
        ...common,
        target_collection_id,
        sample_batch_ids
      })
      break
    }
    case 'delete': {
      confirm.require({
        icon: 'pi pi-exclamation-triangle',
        header: 'Delete collection',
        message: `Are you sure you want to delete '${info.name}' target collection?`,
        accept: () => {
          app.data.target.collection.delete({
            collectionId: info.id,
            collectionName: info.name,
            deleteOrphanCompounds: deleteOrphans.value
          })
          action.value = null
        },
        acceptProps: {
          icon: 'pi pi-trash',
          label: 'Delete',
          severity: 'danger'
        },
        rejectProps: {
          icon: 'pi pi-times',
          label: 'Cancel',
          severity: 'secondary'
        }
      })
      break
    }
  }
  action.value = null
}
const executeLabel = computed(() => (action.value == 'delete' ? 'Delete' : 'Save'))
const invalidated = computed(() => {
  switch (action.value) {
    case 'create':
      return !info.name || !info.type || compounds.created.length + compounds.selected.length == 0

    case 'update': {
      const infoChanged =
        info.name !== original.value.target_collection_name ||
        info.desc !== original.value.target_collection_description ||
        info.type !== original.value.target_collection_type
      const compoundsChanged = !equals(compounds.initial, compounds.selected, 'target_compound_id')
      const compoundsCreated = compounds.created.length > 0 // Check if new compounds were added
      return !(infoChanged || compoundsChanged || compoundsCreated)
    }
    case 'update_batches':
      return equals(batches.initial, batches.selected, 'sample_batch_id')
    default:
      return false
  }
})

const invalidFormula = computed(
  () => add.formula.length > 0 && !isValidChemicalFormula(add.formula)
)

// Check for existing compound in db for manual input
const existingInputCompound = computed(() =>
  findExistingCompound(app.data.target.compound.list, {
    target_compound_formula: add.formula,
    target_compound_name: add.name,
    cas_number: add.cas
  })
)

// Check if compound would be duplicate in current selection
const alreadyInSelection = computed(() => {
  if (!add.formula.trim()) return false

  return (
    compounds.selected.some((comp) =>
      findExistingCompound([comp], {
        target_compound_formula: add.formula,
        target_compound_name: add.name,
        cas_number: add.cas
      })
    ) ||
    compounds.created.some((comp) =>
      findExistingCompound([comp], {
        target_compound_formula: add.formula,
        target_compound_name: add.name,
        cas_number: add.cas
      })
    )
  )
})

// Button configuration for manual input
const addCompoundButtonConfig = computed(() => {
  if (!add.formula.trim()) {
    return {
      label: 'Add compound',
      tooltip: 'Enter formula to add compound'
    }
  }
  if (invalidFormula.value) {
    return {
      label: 'Add compound',
      tooltip: 'Invalid chemical formula'
    }
  }
  if (alreadyInSelection.value) {
    return {
      label: 'Add compound',
      tooltip: 'Compound already in selection'
    }
  }
  if (existingInputCompound.value) {
    return {
      label: 'Add compound',
      severity: 'info',
      tooltip: 'Add existing compound'
    }
  }
  return {
    label: 'Create compound',
    severity: 'primary',
    tooltip: 'Create new compound'
  }
})

const addCompoundButtonDisabled = computed(
  () => !add.formula.trim() || invalidFormula.value || alreadyInSelection.value
)

watch(action, init)
async function init(mode) {
  if (!mode) {
    return
  }
  selected.tab = 'compounds'
  selected.collection = 'all-compounds'
  selected.source = 'collection'
  selected.search = ''
  compounds.loaded = []
  compounds.selected = []
  compounds.initial = []
  compounds.created = []
  add.name = ''
  add.formula = ''
  add.cas = ''
  batches.loaded = []
  batches.selected = []
  if (mode.startsWith('update')) {
    info.id = original.value?.target_collection_id
    info.name = original.value?.target_collection_name
    info.desc = original.value?.target_collection_description
    info.type = original.value?.target_collection_type
    compounds.selected = app.data.match.compound.list.filter(
      (comp) => comp.target_collection_id === original.value.target_collection_id
    )
  }
  switch (mode) {
    case 'create': {
      info.id = ''
      info.name = ''
      info.desc = ''
      info.type = 'TARGETS'
      selected.workspace = app.data.workspace.focused
      batches.selected = app.data.batch.focused ? [app.data.batch.focused] : []
      break
    }
    case 'update_batches': {
      selected.tab = 'batches'
      selected.workspace = app.data.workspace.focused
      batches.selected = (
        await api.http.get(`/target/collections/${original.value.target_collection_id}`, {
          use: 'read',
          type: 'read_target_collection'
        })
      )?.sample_batches
      break
    }
    case 'delete': {
      info.id = original.value?.target_collection_id
      info.name = original.value?.target_collection_name
      deleteOrphans.value = true
    }
  }
  compounds.initial = clone(compounds.selected)
  batches.initial = clone(batches.selected)
}

/**
 * Adds a new compound to the list.
 * This function first checks if the 'Formula' input is not empty,
 * then it adds the compound, and finally, it resets the input fields.
 */
const addCompound = () => {
  if (!add.formula.trim()) {
    return // Prevent adding if formula is empty
  }
  loadSpreadsheet({
    rows: [
      {
        target_compound_formula: add.formula,
        target_compound_name: add.name,
        cas_number: add.cas
      }
    ]
  })
  // Reset input fields
  add.formula = ''
  add.name = ''
  add.cas = ''
}
const onEnter = (event) => {
  if (visible.value && event.code == 'Enter') {
    addCompound()
  }
}
onMounted(() => window.addEventListener('keydown', onEnter))
onBeforeUnmount(() => window.removeEventListener('keydown', onEnter))
</script>

<template>
  <Dialog v-model:visible="visible" :header="title">
    <!-- create or update -->
    <template v-if="['create', 'update', 'update_batches'].includes(action)">
      <div class="row">
        <FloatLabel>
          <InputText
            v-model="info.name"
            id="target-collection-name"
            :disabled="action == 'update_batches'"
            required
          />
          <label for="target-collection-name">Name</label>
        </FloatLabel>
        <FloatLabel style="flex-grow: 1">
          <InputText
            v-model="info.desc"
            id="target-collection-desc"
            :disabled="action == 'update_batches'"
            style="width: 100%"
          />
          <label for="target-collection-desc">Description</label>
        </FloatLabel>
        <SelectButton
          v-model="info.type"
          :options="collectionTypes"
          :allowEmpty="false"
          :disabled="action == 'update_batches'"
        />
      </div>
      <Tabs v-model:value="selected.tab" lazy>
        <TabList>
          <Tab value="compounds" :disabled="action == 'update_batches'">Compounds</Tab>
          <Tab value="batches" :disabled="action == 'update'">Batches</Tab>
        </TabList>
        <TabPanels>
          <!-- compounds -->
          <TabPanel value="compounds">
            <div class="selector">
              <div class="row" style="align-items: stretch; height: 450px">
                <Panel>
                  <div class="row" style="margin-bottom: 1rem; align-items: flex-start">
                    <h4 style="margin: 0" v-if="action == 'update'">Collection changes</h4>
                    <h4 style="margin: 0" v-else-if="action == 'create'">Collection</h4>
                    <span
                      :style="`
                        opacity: 0.5;
                        font-style: italic;
                        max-width: 250px;
                        font-size: smaller;
                        text-align: right;
                      `"
                    >
                      Add compounds by pasting spreadsheet cells here or by using the panel to the
                      right.
                    </span>
                  </div>
                  <BaseClipboardContext
                    hideInitMessage
                    @validated="({ data }) => loadSpreadsheet({ rows: data })"
                    :parse="
                      (text) => {
                        const { rows } = fromSpreadsheet(text, [
                          'target_compound_name',
                          'target_compound_formula',
                          'cas_number' // optional
                        ])
                        return rows
                      }
                    "
                    :validate="
                      (data) => {
                        const cols = Object.keys(data[0]).length
                        const rows = data.length
                        if (cols == 1 && rows == 1) {
                          return {
                            valid: false,
                            severity: 'warn',
                            message: 'Please paste spreadsheet cells'
                          }
                        }
                        const validCols = 2 <= cols && cols <= 3
                        const validRows = data.map(
                          (row) => row?.target_compound_formula?.length > 0
                        )
                        const valid = validRows && validCols
                        const messageCols = !validCols
                          ? `You pasted ${cols} columns but 2 or 3 are expected`
                          : null
                        const messageRows = !validRows
                          ? `Some rows are missing a formula, which is required`
                          : null
                        const message =
                          messageCols ?? messageRows ?? `Pasted ${cols} columns and ${rows} rows`
                        return {
                          valid,
                          severity: valid ? 'success' : 'warn',
                          message
                        }
                      }
                    "
                    :persistMessage="changes.length == 0"
                  >
                    <DataTable
                      dataKey="target_compound_formula"
                      v-if="changes.length"
                      :value="changes"
                      sortMode="multiple"
                      :multiSortMeta="[
                        { field: 'status', order: 1 },
                        { field: 'target_compound_formula', order: 1 }
                      ]"
                      scrollable
                      scrollHeight="360px"
                      :virtualScrollerOptions="{ itemSize: 49.69 }"
                      style="height: 360px; width: 500px"
                    >
                      <Column
                        header="Status"
                        field="status"
                        key="status"
                        columnKey="status"
                        sortable
                      >
                        <template #body="slotProps">
                          <InlineMessage
                            v-if="slotProps.data.status == '1 create'"
                            severity="success"
                          >
                            Create
                          </InlineMessage>
                          <InlineMessage
                            v-else-if="slotProps.data.status == '2 add'"
                            severity="info"
                          >
                            Add
                          </InlineMessage>
                          <InlineMessage
                            v-else-if="slotProps.data.status == '3 keep'"
                            severity="secondary"
                            icon="pi pi-thumbtack"
                          >
                            Keep
                          </InlineMessage>
                          <InlineMessage
                            v-else-if="slotProps.data.status == '4 remove'"
                            severity="warn"
                          >
                            Remove
                          </InlineMessage>
                        </template>
                      </Column>
                      <Column
                        v-for="{ field, label } of columns.filter(
                          ({ field }) => field !== 'status'
                        )"
                        :key="field"
                        :field="field"
                        :header="label"
                        sortable
                      >
                        <template #body="{ data }">
                          <div
                            v-tooltip="data[field]"
                            style="
                              max-width: 100px;
                              white-space: nowrap;
                              overflow: hidden;
                              text-overflow: ellipsis;
                            "
                          >
                            {{ data[field] }}
                          </div>
                        </template>
                      </Column>
                      <Column headerStyle="width: 3rem">
                        <template #body="slotProps">
                          <Button
                            v-if="slotProps.data.status == '4 remove'"
                            @click="restore(slotProps.data)"
                            icon="pi pi-plus"
                            severity="secondary"
                            text
                          />
                          <Button
                            v-else
                            @click="remove(slotProps.data)"
                            icon="pi pi-times"
                            severity="secondary"
                            text
                          />
                        </template>
                      </Column>
                    </DataTable>
                    <i v-else style="margin-bottom: 5rem"> No compounds added yet </i>
                  </BaseClipboardContext>
                </Panel>
                <Panel>
                  <div class="row" style="align-items: flex-start">
                    <h4 style="margin-bottom: 0.5rem">Add compounds</h4>
                    <SelectButton
                      v-model="selected.source"
                      :allowEmpty="false"
                      :options="[
                        {
                          label: 'Import existing',
                          value: 'collection'
                        },
                        { label: 'Create new', value: 'input' }
                      ]"
                      optionLabel="label"
                      optionValue="value"
                    />
                  </div>
                  <div
                    class="row"
                    style="align-items: flex-end"
                    v-if="selected.source == 'collection'"
                  >
                    <FloatLabel>
                      <label>Collection</label>
                      <Select
                        v-model:modelValue="selected.collection"
                        :options="[
                          {
                            target_collection_id: 'all-compounds',
                            target_collection_name: 'All compounds'
                          },
                          ...app.data.target.collection.list.filter((coll) =>
                            action !== 'create'
                              ? coll.target_collection_id !== original.target_collection_id
                              : true
                          )
                        ]"
                        optionLabel="target_collection_name"
                        optionValue="target_collection_id"
                        dataKey="target_collection_id"
                        id="target-collection-source"
                        style="min-width: 200px"
                        filter
                        resetFilterOnHide
                      />
                    </FloatLabel>
                    <FloatLabel style="flex-grow: 1">
                      <IconField class="full">
                        <InputIcon>
                          <i class="pi pi-search" />
                        </InputIcon>
                        <InputText
                          v-model="selected.search"
                          placeholder="Search compounds"
                          style="width: 100%"
                        />
                      </IconField>
                    </FloatLabel>
                  </div>
                  <DataTable
                    v-if="selected.source == 'collection'"
                    :key="key.targets"
                    dataKey="target_compound_id"
                    v-model:selection="compounds.selected"
                    :value="
                      compounds.loaded.filter((comp) => {
                        const query = selected.search.toLowerCase()
                        const nameMatch = comp.target_compound_name.toLowerCase()?.includes(query)
                        const formulaMatch = comp.target_compound_formula
                          ?.toLowerCase()
                          .includes(query)
                        const casMatch = comp.cas_number?.toLowerCase().includes(query)
                        return nameMatch || formulaMatch || casMatch
                      })
                    "
                    sortField="mz"
                    scrollable
                    scrollHeight="310px"
                    :virtualScrollerOptions="{ itemSize: 37.4 }"
                    style="height: 310px; width: 500px"
                  >
                    <Column selectionMode="multiple" header="" headerStyle="width: 3rem">
                      <template #header>
                        <Checkbox
                          :binary="true"
                          v-model="selected.all.targets"
                          :disabled="compounds.loaded.length == 0"
                          @update:modelValue="
                            (select) => {
                              if (select) {
                                const selected = compounds.selected.map(
                                  ({ target_compound_formula }) => target_compound_formula
                                )
                                compounds.selected.push(
                                  ...compounds.loaded.filter(
                                    (loaded) => !selected.includes(loaded.target_compound_formula)
                                  )
                                )
                              } else {
                                const loaded = compounds.loaded.map(
                                  ({ target_compound_formula }) => target_compound_formula
                                )
                                compounds.selected = compounds.selected.filter(
                                  (selected) => !loaded.includes(selected.target_compound_formula)
                                )
                              }
                              key.targets += 1
                            }
                          "
                          inputClass="custom"
                        />
                      </template>
                    </Column>
                    <Column
                      v-for="{ field, label } of columns.filter(({ field }) => field !== 'status')"
                      :key="field"
                      :field="field"
                      :header="label"
                      sortable
                    >
                      <template #body="{ data }">
                        <div
                          v-tooltip="data[field]"
                          style="
                            max-width: 100px;
                            white-space: nowrap;
                            overflow: hidden;
                            text-overflow: ellipsis;
                          "
                        >
                          {{ data[field] }}
                        </div>
                      </template>
                    </Column>
                  </DataTable>
                  <div
                    v-if="selected.source == 'input'"
                    style="min-width: 500px; height: 100%; display: grid; place-items: center"
                  >
                    <div class="col" style="gap: 0.5rem; margin-top: 2rem">
                      <FloatLabel>
                        <InputText v-model="add.formula" id="add-compound-formula" />
                        <label for="add-compound-formula">Formula</label>
                      </FloatLabel>
                      <FloatLabel>
                        <InputText v-model="add.name" id="add-compound-name" />
                        <label for="add-compound-name">Name</label>
                      </FloatLabel>
                      <FloatLabel>
                        <InputText v-model="add.cas" id="add-compound-cas" />
                        <label for="add-compound-cas">CAS Number</label>
                      </FloatLabel>
                      <Button
                        :label="addCompoundButtonConfig?.label ?? 'Add compound'"
                        icon="pi pi-plus"
                        @click="addCompound"
                        :disabled="addCompoundButtonDisabled"
                        :severity="addCompoundButtonConfig?.severity ?? 'primary'"
                        v-tooltip="addCompoundButtonConfig?.tooltip ?? 'Add compound'"
                        style="width: 210px; margin-top: 2rem"
                      />
                    </div>
                  </div>
                </Panel>
              </div>
            </div>
          </TabPanel>
          <!-- batches -->
          <TabPanel value="batches">
            <div class="row" style="height: 400px; align-items: stretch; gap: 0.5rem">
              <Listbox
                v-model="selected.workspace"
                dataKey="workspace_id"
                optionLabel="label"
                :options="filteredWorkspaces"
                scrollHeight="380px"
                :virtualScrollerOptions="{ itemSize: 28.41 }"
                style="min-width: 200px; min-height: 350px"
              />
              <!-- batches -->
              <Panel>
                <DataTable
                  :key="key.batches"
                  dataKey="sample_batch_id"
                  v-model:selection="batches.selected"
                  :value="batches.loaded"
                  scrollable
                  scrollHeight="350px"
                  :virtualScrollerOptions="{ itemSize: 36.34 }"
                  tableStyle="width: 450px;"
                  style="min-width: 500px"
                  sortField="sample_batch_utc_created"
                  :sortOrder="-1"
                >
                  <Column selectionMode="multiple" header="" headerStyle="width: 3rem">
                    <template #header>
                      <Checkbox
                        :binary="true"
                        v-model="selected.all.batches"
                        :disabled="batches.loaded.length == 0"
                        @update:modelValue="
                          (select) => {
                            if (select) {
                              const selected = batches.selected.map(
                                ({ sample_batch_id }) => sample_batch_id
                              )
                              batches.selected.push(
                                ...batches.loaded.filter(
                                  (loaded) => !selected.includes(loaded.sample_batch_id)
                                )
                              )
                            } else {
                              const loaded = batches.loaded.map(
                                ({ sample_batch_id }) => sample_batch_id
                              )
                              batches.selected = batches.selected.filter(
                                (selected) => !loaded.includes(selected.sample_batch_id)
                              )
                            }
                            key.batches += 1
                          }
                        "
                        inputClass="custom"
                      />
                    </template>
                  </Column>
                  <Column header="Batch" field="sample_batch_name">
                    <template #body="{ data }">
                      <div
                        v-tooltip="data.sample_batch_name"
                        style="
                          max-width: 350px;
                          white-space: nowrap;
                          overflow: hidden;
                          text-overflow: ellipsis;
                        "
                      >
                        {{ data.sample_batch_name }}
                      </div>
                    </template>
                  </Column>
                </DataTable>
              </Panel>
            </div>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </template>
    <!-- delete -->
    <template v-else-if="action == 'delete'">
      <p style="max-width: 50ch">
        Would you like to keep or remove compounds from {{ info.name }}
        that are not part of any other collection?
      </p>
      <div class="col" style="align-items: flex-start; margin: 2rem; gap: 1rem">
        <div class="row">
          <RadioButton
            v-model="deleteOrphans"
            :value="true"
            name="orphans"
            inputId="keep-orphans"
          />
          <label for="keep-orphans"> Delete the collection and its unique compounds </label>
        </div>
        <div class="row">
          <RadioButton
            v-model="deleteOrphans"
            :value="false"
            name="orphans"
            inputId="delete-orphans"
          />
          <label for="delete-orphans"> Delete the collection but keep the unique compounds </label>
        </div>
      </div>
    </template>
    <!-- dialog menu -->
    <menu>
      <Button label="Cancel" severity="secondary" @click="action = null" />
      <Button :label="executeLabel" @click="execute" :disabled="invalidated" />
    </menu>
  </Dialog>
</template>

<style scoped>
.row {
  align-items: flex-end;
}
.row > * {
  margin-bottom: 0.5rem;
}

.col {
  display: flex;
  gap: 0.5rem;
}

:deep(.p-panel-header) {
  padding-top: 0;
}
:deep(.p-message) {
  margin: 0;
}
:deep(.p-inline-message) {
  font-size: smaller;
}
:deep(.p-datatable-column-header-content :not(.custom) + .p-checkbox-box) {
  display: none;
}

.expandable {
  overflow: hidden;
  transition: height 1s ease-in-out;
  margin-bottom: 0.5rem;
}

.expandable.expanded {
  height: fit-content;
}
.expandable.collapsed {
  height: 0;
}
</style>
