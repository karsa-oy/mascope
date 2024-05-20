<script setup>
import FloatLabel from 'primevue/floatlabel'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'


import { reactive, computed, watch } from 'vue'

import { genId } from '@/lib/utils'
import { useSampleStore } from '@/stores'

const sampleStore = useSampleStore()

const props = defineProps({
  original: {
    type: Object,
    required: true
  }
})

const visible = defineModel('visible')
const updated = reactive({
  name: 'new template',
  type: props.original.type,
  template: props.original.template.map((field) => ({ key: genId(8, false), ...field }))
})
const title = computed(() => `Create new template based on '${props.original.name}'`)

const addField = () => {
  updated.template.push({
    key: genId(8, false),
    label: 'new field',
    value: '',
    placeholder: 'field label',
    maxlength: 100
  })
}
const removeField = (label) => {
  updated.template = updated.template.filter((f) => f.label !== label)
}

watch(visible, init)
function init(active) {
  if (!active) return
  updated.name = `${props.original.name} (modified)`
  updated.type = props.original.type
  updated.template = props.original.template.map((field) => ({
    key: genId(8, false),
    ...field
  }))
}
</script>

<template>
  <Dialog :header="title" v-model:visible="visible">
    <FloatLabel>
      <InputText id="template-created-name" v-model="updated.name" />
      <label for="template-created-name"> Template Name </label>
    </FloatLabel>

    <div class="editable-field" v-for="field in updated.template" :key="field.key">
      <FloatLabel>
        <InputText
          id="item-field-label"
          v-model="field.label"
          :required="field.required"
          :disabled="field.disabled"
        />
        <label for="item-field-label"> Field Label </label>
      </FloatLabel>
      <Button
        :id="field.label"
        :disabled="field.required"
        @click="() => removeField(field.label)"
        icon="pi pi-trash"
        severity="danger"
      />
    </div>
    <div class="editable-field" style="justify-content: flex-end">
      <Button label="Add field" @click="() => addField()" icon="pi pi-plus" />
    </div>
    <menu>
      <Button label="Cancel" @click="() => (visible = false)" severity="secondary" />
      <Button
        label="Create"
        @click="
          async () => {
            await sampleStore.template.create(updated)
            visible = false
          }
        "
      />
    </menu>
  </Dialog>
</template>

<style scoped>
.template-menu {
  padding: 0;
  margin: 0;
  gap: 0.5rem;
  display: flex;
  flex-flow: row nowrap;
  align-items: baseline;
  justify-content: flex-end;
}
.template-menu :deep(*) {
  margin: 0;
}
.editable-field {
  display: flex;
  flex-flow: row nowrap;
  align-items: baseline;
  gap: 0.5rem;
  margin: 1rem 0;
}
.editable-field :deep(.p-float-label) {
  margin-bottom: 0;
}
</style>
