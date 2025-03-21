<script setup>
import { ref } from 'vue'

import Button from 'primevue/button'
import InputText from 'primevue/inputtext'

const { field, save } = defineProps({
  field: {
    required: true,
    type: String
  },
  save: {
    required: true,
    type: Function
  }
})

const emit = defineEmits(['saved', 'canceled'])

const editing = ref(false)
const edited = ref(field)
</script>

<template>
  <span class="field">
    <template v-if="!editing">
      <span v-if="!editing">{{ field }}</span>
      <Button
        v-if="field && String(field).length > 0"
        v-tooltip.bottom="{ value: 'Edit field', showDelay: 2000 }"
        icon="pi pi-pen-to-square"
        severity="secondary"
        text
        size="small"
        @click="
          async (event) => {
            event.stopPropagation()
            editing = true
          }
        "
      />
    </template>
    <template v-else>
      <InputText v-model="edited" />
      <Button
        v-tooltip.bottom="'Cancel'"
        icon="pi pi-times"
        severity="secondary"
        text
        size="small"
        @click="
          async (event) => {
            event.stopPropagation()
            edited = field // reset value
            editing = false
            emit('canceled')
          }
        "
      />
      <Button
        v-tooltip.bottom="'Save'"
        icon="pi pi-check"
        severity="secondary"
        text
        size="small"
        @click="
          async (event) => {
            event.stopPropagation()
            await save(edited)
            editing = false
            emit('saved')
          }
        "
      />
    </template>
  </span>
</template>

<style scoped>
.field {
  display: flex;
  flex-flow: row;
  align-items: center;
}

.field > :deep(button) {
  visibility: hidden;
}

.field:hover > :deep(button) {
  visibility: visible;
}

:deep(button) {
  width: min-content;
  margin-left: 0.5rem;
  padding: 5px 7px;
}
</style>
