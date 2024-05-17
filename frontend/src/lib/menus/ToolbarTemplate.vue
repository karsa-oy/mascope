<script setup>
import FloatLabel from 'primevue/floatlabel'
import Select from 'primevue/select'
import { useConfirm } from 'primevue/useconfirm'

import { ref, computed } from 'vue'

import DialogTemplateCreate from '@/lib/dialogs/DialogTemplateCreate.vue'
import { useAppStore, useSampleStore } from '@/stores'

const confirm = useConfirm()

const appStore = useAppStore()
const sampleStore = useSampleStore()

const props = defineProps({
  initial: {
    type: Object,
    required: true
  }
})

const dialog = ref(false)
const template = defineModel('template')

const templates = computed(() => [
  props.initial,
  ...appStore.attributeTemplates.filter((temp) => temp.type == 'sample_item')
])
</script>

<template>
  <menu class="template-menu">
    <Button
      :disabled="!template?.name || template.name == 'default'"
      @click="
        confirm.require({
          header: 'Delete template',
          message: `Are you sure you want to delete template ${template.name}?`,
          icon: 'pi pi-exclamation-triangle',
          rejectLabel: 'Cancel',
          acceptLabel: 'Delete',
          accept: () => {
            sampleStore.template.delete(template)
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
.editable-field :deep(.p-float-label) {
  margin-bottom: 0;
}
</style>
