<script setup>
/**
 * Component for managing ionization modes
 *
 * Allows adding, editing and deleting ionization modes.
 */
import { reactive, computed, watch, ref } from 'vue'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import FloatLabel from 'primevue/floatlabel'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import { useConfirm } from 'primevue/useconfirm'

import { useApp } from '@/stores'

const app = useApp()
const confirm = useConfirm()

const add = reactive({
  ionization_mode_name: '',
  ionization_mode_token: '',
  ionization_mode_polarity: null,
  ionization_mechanism_ids: [],
  calibration_collection_id: null,
  diagnostic_collection_id: null
})

const edited = ref(null)

const resetFields = () => {
  add.ionization_mode_name = ''
  add.ionization_mode_token = ''
  add.ionization_mode_polarity = null
  add.ionization_mechanism_ids = []
  add.calibration_collection_id = null
  add.diagnostic_collection_id = null
}

const resetEdit = () => {
  edited.value = null
}

const editing = (data) => data.ionization_mode_id === edited.value?.ionization_mode_id

// Options
const polarityOptions = [
  { label: '+', value: '+' },
  { label: '-', value: '-' }
]

const calibrationCollections = computed(() =>
  app.data.target.collection.list.filter((c) => c.target_collection_type === 'CALIBRANTS')
)

const diagnosticCollections = computed(() =>
  app.data.target.collection.list.filter((c) => c.target_collection_type === 'DIAGNOSTICS')
)

// Filter mechanisms by selected polarity
const availableMechanisms = computed(() => {
  if (!add.ionization_mode_polarity) {
    return []
  }
  return app.data.ionization.mechanism.list.filter(
    (m) => m.ionization_mechanism_polarity === add.ionization_mode_polarity
  )
})

// Mode operations
const mode = {
  edit: (data) => {
    edited.value = {
      ionization_mode_id: data.ionization_mode_id,
      ionization_mode_name: data.ionization_mode_name,
      ionization_mode_token: data.ionization_mode_token,
      calibration_collection_id: data.calibration_collection_id,
      diagnostic_collection_id: data.diagnostic_collection_id
    }
  },
  cancel: resetEdit,
  save: async () => {
    if (edited.value) {
      const { ionization_mode_id, ...updateData } = edited.value
      await app.data.ionization.mode.update(ionization_mode_id, updateData)
      resetEdit()
    }
  },
  delete: (data) => {
    confirm.require({
      icon: 'pi pi-exclamation-triangle',
      header: `Delete ionization mode '${data.ionization_mode_name}'`,
      message: `Are you sure you want to delete the ionization mode '${data.ionization_mode_name}'?`,
      accept: () => {
        app.data.ionization.mode.delete(data.ionization_mode_id)
      },
      acceptProps: {
        icon: 'pi pi-trash',
        label: 'Delete',
        severity: 'danger'
      },
      rejectProps: {
        label: 'Cancel',
        severity: 'secondary'
      }
    })
  }
}

// Reset mechanisms when polarity changes
watch(
  () => add.ionization_mode_polarity,
  () => {
    add.ionization_mechanism_ids = []
  }
)

// Reset when create successful
watch(
  computed(() => app.data.ionization.mode.list.length),
  (newVal, oldVal) => {
    if (newVal > oldVal) {
      resetFields()
    }
  }
)

// Expose resetFields for parent component
defineExpose({
  resetFields
})
</script>

<template>
  <menu class="row" style="margin-top: 1.5rem; gap: 0.5rem; flex-wrap: wrap">
    <FloatLabel style="flex-grow: 1; min-width: 200px">
      <InputText
        v-model="add.ionization_mode_name"
        id="add-mode-name"
        style="width: 100%"
        v-tooltip="{
          value: 'Enter a descriptive name for the ionization mode (e.g. Nitrate)',
          showDelay: 1000
        }"
      />
      <label for="add-mode-name">Mode Name*</label>
    </FloatLabel>

    <FloatLabel style="flex-grow: 1; min-width: 150px">
      <InputText
        v-model="add.ionization_mode_token"
        id="add-mode-token"
        style="width: 100%"
        v-tooltip="{
          value: 'Enter a short token used in filenames to identify this mode (e.g., _NO3_)',
          showDelay: 1000
        }"
      />
      <label for="add-mode-token">Filename token</label>
    </FloatLabel>

    <FloatLabel style="flex-grow: 1; min-width: 120px">
      <Select
        v-model="add.ionization_mode_polarity"
        :options="polarityOptions"
        optionLabel="label"
        optionValue="value"
        id="add-polarity"
        style="width: 100%"
        v-tooltip="{ value: 'Select the ion polarity for this mode', showDelay: 1000 }"
      />
      <label for="add-polarity">Polarity*</label>
    </FloatLabel>

    <FloatLabel style="flex-grow: 2; min-width: 200px">
      <MultiSelect
        v-model="add.ionization_mechanism_ids"
        :options="availableMechanisms"
        :disabled="!add.ionization_mode_polarity"
        :showToggleAll="false"
        optionLabel="ionization_mechanism"
        optionValue="ionization_mechanism_id"
        id="add-mechanisms"
        style="width: 100%"
        :placeholder="add.ionization_mode_polarity ? 'Select mechanisms' : 'Select polarity first'"
        v-tooltip="{
          value:
            'Choose one or more ionization mechanisms to apply for files acquired in this mode',
          showDelay: 1000
        }"
      />
      <label for="add-mechanisms">Mechanisms*</label>
    </FloatLabel>

    <FloatLabel style="flex-grow: 1; min-width: 180px">
      <Select
        v-model="add.calibration_collection_id"
        :options="calibrationCollections"
        optionLabel="target_collection_name"
        optionValue="target_collection_id"
        id="add-calibration"
        style="width: 100%"
        v-tooltip="{
          value: 'Select a target collection for this ionization mode to use for mass calibration',
          showDelay: 1000
        }"
      />
      <label for="add-calibration">Calibration Collection</label>
    </FloatLabel>

    <FloatLabel style="flex-grow: 1; min-width: 180px">
      <Select
        v-model="add.diagnostic_collection_id"
        :options="diagnosticCollections"
        optionLabel="target_collection_name"
        optionValue="target_collection_id"
        id="add-diagnostic"
        style="width: 100%"
        v-tooltip="{
          value: 'Select a target collection for this ionization mode to use for quality control',
          showDelay: 1000
        }"
      />
      <label for="add-diagnostic">Diagnostic Collection</label>
    </FloatLabel>

    <Button
      label="Add"
      icon="pi pi-plus"
      @click="
        () =>
          app.data.ionization.mode.create({
            ionization_mode_name: add.ionization_mode_name.trim(),
            ionization_mode_token: add.ionization_mode_token.trim() || null,
            ionization_mode_polarity: add.ionization_mode_polarity,
            ionization_mechanism_ids: add.ionization_mechanism_ids,
            calibration_collection_id: add.calibration_collection_id,
            diagnostic_collection_id: add.diagnostic_collection_id
          })
      "
      :disabled="
        !add.ionization_mode_name.trim() ||
        !add.ionization_mode_polarity ||
        !add.ionization_mechanism_ids.length
      "
      style="align-self: flex-end"
      v-tooltip="{ value: 'Add this ionization mode to the database', showDelay: 1000 }"
    />
  </menu>

  <section style="margin: 1rem 0">
    <DataTable
      :value="app.data.ionization.mode.list"
      scrollable
      scrollHeight="calc(85vh - 300px)"
      tableStyle="min-width: 800px"
    >
      <Column header="Name" style="min-width: 150px">
        <template #body="{ data }">
          <InputText
            v-if="editing(data)"
            v-model="edited.ionization_mode_name"
            style="width: 100%"
          />
          <span v-else>{{ data.ionization_mode_name }}</span>
        </template>
      </Column>

      <Column header="Filename token" style="min-width: 120px">
        <template #body="{ data }">
          <InputText
            v-if="editing(data)"
            v-model="edited.ionization_mode_token"
            style="width: 100%"
          />
          <span v-else>{{ data.ionization_mode_token || '' }}</span>
        </template>
      </Column>

      <Column header="Polarity" style="width: 120px">
        <template #body="{ data }">
          {{ data.ionization_mode_polarity }}
        </template>
      </Column>

      <Column header="Mechanisms" style="min-width: 200px">
        <template #body="{ data }">
          <div style="display: flex; flex-wrap: wrap; gap: 0.25rem">
            <span
              v-for="mechanismId in data.ionization_mechanism_ids"
              :key="mechanismId"
              class="mechanism-tag"
            >
              {{
                app.data.ionization.mechanism.list.find(
                  (m) => m.ionization_mechanism_id === mechanismId
                )?.ionization_mechanism || mechanismId
              }}
            </span>
          </div>
        </template>
      </Column>

      <Column header="Calibration Collection" style="min-width: 150px">
        <template #body="{ data }">
          <Select
            v-if="editing(data) && data.calibration_collection_id === null"
            v-model="edited.calibration_collection_id"
            :options="calibrationCollections"
            optionLabel="target_collection_name"
            optionValue="target_collection_id"
            id="edit-calibration"
            style="width: 100%"
            v-tooltip="{
              value:
                'Select a target collection for this ionization mode to use for mass calibration',
              showDelay: 1000
            }"
          />
          <span v-else>
            {{
              data.calibration_collection_id
                ? app.data.target.collection.list.find(
                    (c) => c.target_collection_id === data.calibration_collection_id
                  )?.target_collection_name || data.calibration_collection_id
                : ''
            }}
          </span>
        </template>
      </Column>

      <Column header="Diagnostic Collection" style="min-width: 150px">
        <template #body="{ data }">
          <Select
            v-if="editing(data) && data.diagnostic_collection_id === null"
            v-model="edited.diagnostic_collection_id"
            :options="diagnosticCollections"
            optionLabel="target_collection_name"
            optionValue="target_collection_id"
            id="edit-diagnostic"
            style="width: 100%"
            v-tooltip="{
              value:
                'Select a target collection for this ionization mode to use for quality control',
              showDelay: 1000
            }"
          />
          <span v-else>
            {{
              data.diagnostic_collection_id
                ? app.data.target.collection.list.find(
                    (c) => c.target_collection_id === data.diagnostic_collection_id
                  )?.target_collection_name || data.diagnostic_collection_id
                : ''
            }}
          </span>
        </template>
      </Column>

      <Column style="width: 120px">
        <template #body="{ data }">
          <div class="row" style="justify-content: flex-end; gap: 0.25rem">
            <template v-if="editing(data)">
              <Button
                v-tooltip="{ value: 'Cancel editing', showDelay: 1000 }"
                icon="pi pi-times"
                text
                size="small"
                severity="secondary"
                @click="mode.cancel"
              />
              <Button
                v-tooltip="{ value: 'Save changes', showDelay: 1000 }"
                icon="pi pi-check"
                text
                size="small"
                severity="secondary"
                @click="mode.save"
              />
            </template>
            <template v-else>
              <Button
                v-tooltip="{ value: 'Edit ionization mode', showDelay: 1000 }"
                icon="pi pi-pencil"
                text
                size="small"
                @click="mode.edit(data)"
              />
              <Button
                v-tooltip="{ value: 'Delete ionization mode', showDelay: 1000 }"
                icon="pi pi-trash"
                text
                size="small"
                @click="mode.delete(data)"
              />
            </template>
          </div>
        </template>
      </Column>
    </DataTable>
  </section>
</template>

<style scoped>
.row {
  display: flex;
  align-items: flex-start;
}

.mechanism-tag {
  background: var(--p-primary-100);
  color: var(--p-primary-900);
  padding: 0.25rem 0.5rem;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 500;
}
</style>
