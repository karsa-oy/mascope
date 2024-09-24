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
import Avatar from 'primevue/avatar'
import { useConfirm } from 'primevue/useconfirm'

import { api } from '@/api'
import { useApp } from '@/stores'
import { fromSpreadsheet, equals } from '@/lib/table'
import { BaseClipboardContext } from '@/lib/base'
import { clone } from '@/lib/utils'
import { collectionTypes } from '@/lib/constants'

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
  source: null, // for adding compounds
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
      title = `Create a new target collection "${info.name}" and add to ${batchLabel.value}`
      break
    case 'update':
      title = `Edit target collection "${info.name}"`
      break
    case 'update_batches':
      title = `Manage batches of "${info.name}" target collection`
      break
    case 'delete':
      title = `Delete target collection "${info.name}"`
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

function remove(compound) {
  if (compound.status == '1 create') {
    compounds.created = compounds.created.filter(
      (selected) => selected.target_compound_formula !== compound.target_compound_formula
    )
  } else {
    compounds.selected = compounds.selected.filter(
      (selected) => selected.target_compound_formula !== compound.target_compound_formula
    )
  }
}
function restore(compound) {
  compounds.selected.push(compound)
}

watchEffect(async () => {
  let pending = []
  if (!selected.source || selected.source == 'Selection') {
    return
  } else if (selected.source === 'All') {
    pending = app.data.target.compound.list
  } else if (selected.source) {
    const id = app.data.target.collection.list.find(
      ({ target_collection_name }) => target_collection_name == selected.source
    ).target_collection_id
    const collection = await app.data.target.collection.read(id)
    pending = collection?.target_compounds ?? []
  }
  if (pending.length) {
    loadCompounds(pending)
  }
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
function loadCompounds(data) {
  const index = new Map(
    [...compounds.selected, ...data].map((compound) => [
      compound.target_compound_id ?? compound.target_compound_formula,
      compound
    ])
  )
  // reconcile with exisiting compounds
  const reconciled = data.map(
    (compound) =>
      index.get(compound.target_compound_id ?? compound.target_compound_formula) ?? compound
  )
  if (selected.source !== 'Selection') {
    compounds.loaded = reconciled
  } else {
    const unselected = (added) =>
      !compounds.selected.find(
        (selected) => selected.target_compound_formula == added.target_compound_formula
      )
    compounds.selected.push(...reconciled.filter(unselected))
  }
}
function loadSpreadsheet({ rows }) {
  let prexisting = []
  rows.forEach((compound) => {
    const record = app.data.target.compound.list.find(
      (comp) => comp.target_compound_formula === compound.target_compound_formula
    )
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
  loadCompounds(prexisting)
}

watchEffect(() => loadBatches(selected.workspace))

async function loadBatches(workspace) {
  if (workspace) {
    const latest = (
      await api.request.read({
        method: 'getAllBatches',
        body: {
          workspace_id: workspace.workspace_id
        },
        errorMessage: `Failed to load the workspace batches.`
      })
    ).data
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
}

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
        header: 'Delete collection',
        message: `Are you sure you want to delete '${info.name}' target collection?`,
        rejectIcon: 'pi pi-times',
        rejectLabel: 'Cancel',
        acceptIcon: 'pi pi-trash',
        acceptLabel: 'Delete',
        accept: () => {
          app.data.target.collection.delete({
            collectionId: info.id,
            collectionName: info.name,
            deleteOrphanCompounds: deleteOrphans.value
          })
          action.value = null
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

watch(action, init)
async function init(mode) {
  if (!mode) {
    return
  }
  selected.tab = 'compounds'
  selected.source = 'Selection'
  compounds.loaded = []
  compounds.selected = []
  compounds.initial = []
  compounds.created = []
  add.expanded = false
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
    compounds.selected = original.value?.target_compounds ?? original.value?.children ?? []
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
        await api.request.read({
          method: 'getTargetCollection',
          body: original.value.target_collection_id
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
  loadBatches(selected.workspace)
}

/**
 * Checks if any of the 'add compound' input fields are focused.
 * If none of the relevant fields are focused, it collapses the add compound panel.
 *
 * @param {Event} event - The blur event that triggers this function.
 */
function addCheckFocus(event) {
  // Get the active element (the currently focused element)
  const activeElement = document.activeElement

  // Check if the active element is not any of the inputs in the panel
  if (
    activeElement.id !== 'add-compound-formula' &&
    activeElement.id !== 'add-compound-name' &&
    activeElement.id !== 'add-compound-cas'
  ) {
    add.expanded = false
  }
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
  if (event.code == 'Enter') {
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
      <Tabs v-model:value="selected.tab">
        <TabList>
          <Tab value="compounds" :disabled="action == 'update_batches'">Compounds</Tab>
          <Tab value="batches" :disabled="action == 'update'">Batches</Tab>
        </TabList>
        <TabPanels>
          <!-- compounds -->
          <TabPanel value="compounds">
            <div class="row selector">
              <Listbox
                v-model="selected.source"
                :options="[
                  'Selection',
                  'All',
                  ...app.data.target.collection.list
                    .filter((coll) =>
                      action !== 'create'
                        ? coll.target_collection_id !== original.target_collection_id
                        : true
                    )
                    .map((coll) => coll.target_collection_name)
                ]"
                id="target-collection-source"
                style="min-width: 200px; height: 300px"
              >
                <template #option="slotProps">
                  <div style="display: flex; flex-flow: row; gap: 0.5rem; align-items: center">
                    <Avatar
                      :icon="`pi ${slotProps.option == 'Selection' ? 'pi-list-check' : 'pi-book'}`"
                      shape="circle"
                    />
                    <span>{{ slotProps.option }}</span>
                  </div>
                </template>
              </Listbox>
              <Panel>
                <div class="row">
                  <Button
                    :icon="add.expanded ? 'pi pi-chevron-down' : 'pi pi-chevron-right'"
                    @click="add.expanded = !add.expanded"
                    text
                  />
                  <FloatLabel style="flex-grow: 1">
                    <InputText
                      v-model="add.formula"
                      id="add-compound-formula"
                      style="width: 100%"
                      @focus="add.expanded = true"
                      @blur="addCheckFocus"
                      :invalid="!add.formula.trim() && add.expanded"
                    />
                    <label for="add-compound-formula">Formula*</label>
                  </FloatLabel>
                  <Button
                    label="Add"
                    icon="pi pi-plus"
                    @click="addCompound"
                    :disabled="!add.formula.trim()"
                  />
                </div>
                <div
                  :class="`row expandable ${add.expanded ? 'expanded' : 'collapsed'}`"
                  style="padding-left: 5ch"
                >
                  <FloatLabel>
                    <InputText
                      v-model="add.name"
                      id="add-compound-name"
                      @focus="add.expanded = true"
                      @blur="addCheckFocus"
                    />
                    <label for="add-compound-name">Name</label>
                  </FloatLabel>
                  <FloatLabel>
                    <InputText
                      v-model="add.cas"
                      id="add-compound-cas"
                      @focus="add.expanded = true"
                      @blur="addCheckFocus"
                    />
                    <label for="add-compound-cas">CAS Number</label>
                  </FloatLabel>
                </div>
                <BaseClipboardContext
                  v-if="selected.source == 'Selection'"
                  info="You can also add compounds by pasting spreadsheet cells"
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
                      const validRows = data.map((row) => row?.target_compound_formula?.length > 0)
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
                    :scrollHeight="add.expanded ? '130px' : '200px'"
                    style="flex-grow: 1"
                  >
                    <Column header="Status" field="status" key="status" columnKey="status" sortable>
                      <template #body="slotProps">
                        <InlineMessage
                          v-if="slotProps.data.status == '1 create'"
                          severity="success"
                        >
                          Create
                        </InlineMessage>
                        <InlineMessage v-else-if="slotProps.data.status == '2 add'" severity="info">
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
                      v-for="col of columns.filter(({ field }) => field !== 'status')"
                      :key="col.field"
                      :field="col.field"
                      :header="col.label"
                      sortable
                    />
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
                <div v-else class="grid">
                  <DataTable
                    :key="key.targets"
                    dataKey="target_compound_id"
                    v-model:selection="compounds.selected"
                    :value="compounds.loaded"
                    sortField="mz"
                    scrollable
                    scrollHeight="250px"
                    style="min-width: 400px"
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
                      v-for="col of columns.filter(({ field }) => field !== 'status')"
                      :key="col.field"
                      :field="col.field"
                      :header="col.label"
                      sortable
                    />
                  </DataTable>
                </div>
              </Panel>
            </div>
          </TabPanel>
          <!-- batches -->
          <TabPanel value="batches">
            <div class="row selector">
              <Listbox
                v-model="selected.workspace"
                dataKey="workspace_id"
                optionLabel="label"
                :options="
                  app.data.workspace.list
                    .sort((a, b) => {
                      // ensure the current workspace comes first
                      if (a.workspace_id == app.data.workspace.focused.workspace_id) return -1
                      if (b.workspace_id == app.data.workspace.focused.workspace_id) return 1
                      return 0
                    })
                    .map((workspace, index) => ({
                      // create labels, demarcating the current one
                      ...workspace,
                      label:
                        index > 0
                          ? workspace.workspace_name
                          : `${workspace.workspace_name} (current)`
                    }))
                "
                style="min-width: 200px"
              />
              <!-- batches -->
              <DataTable
                :key="key.batches"
                dataKey="sample_batch_id"
                v-model:selection="batches.selected"
                :value="batches.loaded"
                scrollable
                scrollHeight="300px"
                tableStyle="min-width: 450px; "
                style="min-width: 400px"
                sortField="sample_batch_name"
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
                <Column header="Batch" field="sample_batch_name" />
              </DataTable>
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
.grid {
  min-width: 300px;
  min-height: 150px;
  height: 100%;
  display: grid;
  place-items: center;
  gap: 0.5rem;
}

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

.selector > * {
  min-height: 300px;
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
