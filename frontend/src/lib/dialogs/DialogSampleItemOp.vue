<script setup>
import { ref, computed, watch, watchEffect, reactive } from 'vue'

import FloatLabel from 'primevue/floatlabel'
import Select from 'primevue/select'
import ScrollPanel from 'primevue/scrollpanel'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Panel from 'primevue/panel'
import Dialog from 'primevue/dialog'

import { ToolbarTemplate } from '@/lib/toolbars'
import { clone, strToSnakeCase, beautifySnakeCase, genId } from '@/lib/utils'
import { useApp } from '@/stores'

const app = useApp()

const props = defineProps({
  item: {
    type: Object
  }
})

const original = computed(() => props.item)

// dialog visibility reactivity
const action = defineModel('action') // create, create_pending update
const visible = ref(false)
watch(action, (value) => {
  visible.value = !!value
})
watch(visible, (value) => {
  if (!value) {
    action.value = null
  }
})

const initial = computed(() => ({
  name: 'default',
  type: 'sample_item',
  template: [
    // name is always required
    {
      label: 'sample_item_name',
      value: original.value?.sample_item_name,
      required: true,
      placeholder: 'Sample title'
    },
    // and any attributes from the item
    ...Object.entries(original.value?.sample_item_attributes ?? {}).map(([label, value]) => ({
      label,
      value
    }))
  ]
}))

const template = reactive({
  selected: initial.value
})
const input = reactive({
  fields: template.selected.template,
  filename: null,
  filterId: null,
  instrument: null,
  type: null
})
const state = reactive({
  tab: 'info'
})

const title = computed(
  () =>
    ({
      create: `Create a new sample item`,
      create_pending: `Create a new sample item`,
      update: `Update sample item "${original.value?.sample_item_name}"`
    })[action.value]
)

// component initialization logic
watch(visible, init)
function init(active) {
  if (!active) return
  // reset state
  state.tab = 'info'
  template.selected = initial.value
  // reset inputs
  input.filename =
    action.value !== 'create_pending'
      ? original.value?.filename
      : app.data.acquisition.pending.filename
  input.instrument = original.value?.instrument
  input.filterId = original.value?.filter_id ?? null
  input.type = original.value?.sample_item_type ?? null
  // fill fields
  input.fields = Object.entries({
    sample_item_name: original.value?.sample_item_name,
    ...original.value?.sample_item_attributes
  }).map(([label, value]) => ({
    label,
    value
  }))
}
// autofill fields when template is selected
watch(template, autofill)
function autofill() {
  const loaded = template.selected
  if (loaded) {
    input.fields = loaded.template.map((newField) => ({
      ...newField,
      value: input.fields.find((oldField) => oldField.label === newField.label)?.value
    }))
  }
}

const generated = reactive({
  filterId: null
})
const filters = computed(() => {
  return app.data.batch.focused
    ? [
        null,
        ...(generated.filterId ? [generated.filterId] : []),
        ...new Set(app.data.sample.list.map(({ filter_id }) => filter_id).filter((f) => f))
      ]
    : [generated.filterId]
})

async function save() {
  const sample_item = {
    sample_item_name: input.fields.find((field) => field.label == 'sample_item_name').value,
    sample_item_type: input.type,
    sample_batch_id: app.data.batch.focused.sample_batch_id,
    filter_id: input.filterId,
    sample_item_attributes: clone(
      input.fields
        .filter((field) => field.label != 'sample_item_name')
        .reduce(
          (fields, field) => ({
            ...fields,
            [strToSnakeCase(field.label)]: field.value ?? ''
          }),
          {}
        ) ?? {}
    )
  }
  if (props.action == 'create') {
    await app.data.sample.process({
      filename: input.filename,
      ...sample_item
    })
  } else if (props.action == 'create_pending') {
    if (!(app.data.acquisition.ready.filename == input.filename)) {
      // submitted before conversion completed
      app.data.acquisition.pending.sample = {
        ...sample_item,
        filename: app.data.acquisition.pending.filename
      }
    } else {
      // submitted after conversion completed
      app.data.sample.process({
        ...sample_item,
        filename: input.filename
      })
      app.data.acquisition.ready.filename = null
    }
    app.data.acquisition.pending.filename = null
  } else if (props.action == 'update') {
    await app.data.sample.update({
      ...props.item, // To include sample_item_id
      ...sample_item,
      filename: input.filename
    })
  }
  visible.value = null
}

// reset item type when filter ID was changed
watchEffect(() => {
  if (input.filterId !== original.value?.filter_id) {
    input.type = null
  }
})
watchEffect(() => {
  if (input.type == 'INSTRUMENT_BACKGROUND') {
    input.filterId = null
  }
})
</script>

<template>
  <Dialog
    :header="title"
    v-model:visible="visible"
    style="width: 800px"
    contentStyle="flex-grow: 1; display: flex; flex-flow: column; gap: 0.5rem; justify-content: space-between"
  >
    <Panel>
      <ScrollPanel style="width: 100%; height: 35vh">
        <div class="sample-field-grid">
          <FloatLabel v-for="field in input.fields" :key="field.label">
            <InputText :id="`field-${field.label}`" v-model="field.value" required />
            <label :for="`field-${field.label}`"> {{ beautifySnakeCase(field.label) }} </label>
          </FloatLabel>

          <div class="item-filter">
            <FloatLabel>
              <Select inputId="item-filter-id" v-model="input.filterId" :options="filters" />
              <label for="item-filter-id">Filter ID</label>
            </FloatLabel>
            <Button
              @click="input.filterId = generated.filterId = genId(6, false)"
              icon="pi pi-sparkles"
            />
          </div>

          <FloatLabel>
            <Select
              inputId="item-type"
              v-model="input.type"
              :options="
                input.filterId
                  ? input.filterId == generated.filterId
                    ? [
                        { label: 'Filter Regeneration', value: 'FILTER_REGENERATION' },
                        { label: 'Filter Background', value: 'FILTER_BACKGROUND' }
                      ]
                    : [
                        { label: 'Sample', value: 'SAMPLE' },
                        { label: 'Blank', value: 'BLANK' },
                        { label: 'Filter Background', value: 'FILTER_BACKGROUND' },
                        { label: 'Unknown', value: 'UNKNOWN' }
                      ]
                  : [{ label: 'Instrument Background', value: 'INSTRUMENT_BACKGROUND' }]
              "
              dataKey="value"
              optionValue="value"
              optionLabel="label"
            />
            <label for="item-type"> Sample type </label>
          </FloatLabel>

          <FloatLabel>
            <InputText id="item-filename" v-model="input.filename" required disabled />
            <label for="item-filename"> Filename </label>
          </FloatLabel>
        </div>
      </ScrollPanel>
    </Panel>
    <menu>
      <ToolbarTemplate v-model:template="template.selected" :initial="initial" />
      <menu>
        <Button label="Cancel" @click="() => (action = null)" severity="secondary" />
        <Button
          label="Save"
          @click="() => save()"
          :disabled="
            !input.type ||
            input.fields?.filter((f) => f?.required).length !=
              input.fields?.filter((f) => f?.required).filter((f) => f.value).length
          "
        />
      </menu>
    </menu>
  </Dialog>
</template>

<style scoped>
.sample-field-grid {
  margin: 1rem auto;
  width: 90%;
  min-height: 100%;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(30ch, 100%), 1fr));
  grid-auto-rows: auto;
  align-items: baseline;
  justify-items: start;
  justify-content: center;
  align-content: center;
  gap: 5rem;
}
.item-filter {
  padding: 0;
  margin: 0;
  gap: 0.5rem;
  display: flex;
  flex-flow: row nowrap;
  align-items: baseline;
}
.item-filter :deep(*) {
  margin: 0;
}

:deep(.p-select),
:deep(.p-inputtext) {
  min-width: 250px;
}

menu {
  justify-content: space-between;
}
</style>
