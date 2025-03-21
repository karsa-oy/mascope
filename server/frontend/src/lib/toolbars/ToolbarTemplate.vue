<script setup>
import { ref, computed, watchEffect } from 'vue'

import FloatLabel from 'primevue/floatlabel'
import Select from 'primevue/select'
import Button from 'primevue/button'
import { useConfirm } from 'primevue/useconfirm'

import { DialogTemplateCreate } from '@/lib/dialogs'
import { useApp } from '@/stores'

const confirm = useConfirm()

const app = useApp()

const props = defineProps({
  default: {
    type: Object,
    required: true
  }
})

const dialog = ref(false)
const template = defineModel('template')

const templates = computed(() => [
  props.default,
  ...app.data.template.list.filter((temp) => temp.type == 'sample_item')
])

watchEffect(() => {
  const removed = !app.data.template.list
    .map((temp) => temp.attribute_template_id)
    .includes(template.value?.attribute_template_id)
  if (removed) {
    template.value = props.default
  }
})
</script>

<template>
  <menu class="template-menu">
    <Button
      :disabled="!template?.name || template.name == 'default'"
      @click="
        confirm.require({
          icon: 'pi pi-exclamation-triangle',
          header: 'Delete template',
          message: `Are you sure you want to delete template ${template.name}?`,
          accept: () => {
            app.data.template.delete(template)
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
      "
      severity="danger"
      icon="pi pi-trash"
      iconPos="right"
    />
    <FloatLabel>
      <Select
        inputId="template-loaded"
        v-model="template"
        :options="templates"
        dataKey="attribute_template_id"
        optionLabel="name"
      />
      <label for="templated-loaded"> Template </label>
    </FloatLabel>
    <Button
      @click="dialog = true"
      severity="secondary"
      icon="pi pi-pen-to-square"
      iconPos="right"
    />
  </menu>
  <DialogTemplateCreate v-model:visible="dialog" :original="template" />
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
  margin: 0.5rem 0;
}
.editable-field :deep(.p-floatlabel) {
  margin-bottom: 0;
}
</style>
