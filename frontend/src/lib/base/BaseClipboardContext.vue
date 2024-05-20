<script setup>
import { watch } from 'vue'

import Message from 'primevue/message'

import { useKeyStore } from '@/stores'

const keyStore = useKeyStore()

const data = defineModel('data')
const status = defineModel('status')

const props = defineProps({
  parse: {
    type: Function,
    default: (text) => text
  },
  validate: {
    type: Function, // (parsed) => ({
    //   valid: Boolean,
    //   severity: 'success' | 'error' | 'info' | 'warning' | 'primary' | 'secondary',
    //   message: String
    // })
    default: () => ({
      valid: true,
      severity: 'info',
      message: 'Data pasted succesfully'
    })
  },
  info: {
    type: String,
    required: false,
    default: 'Paste here'
  }
})

const emit = defineEmits(['validated', 'invalidated'])

const show = (severity, message) => {
  status.value = { severity, message }
  setTimeout(() => {
    status.value = null
  }, 3500)
}

watch(keyStore, process)
async function process() {
  if (keyStore.state.control && keyStore.state.v) {
    navigator.permissions.query({ name: 'clipboard-read' })
    let text = await navigator.clipboard.readText()
    let result
    try {
      result = props.parse(text)
    } catch (err) {
      console.warn('Failed to parse clipboard paste', err)
      show('error', 'Failed to process the data you pasted')
      return
    }
    const { valid, severity, message } = props.validate(result)
    show(severity, message)
    if (valid) {
      data.value = result
      emit('validated', {
        data: data.value,
        severity,
        message
      })
    } else {
      emit('invalidated', {
        data: data.value,
        severity,
        message
      })
    }
  }
}
</script>

<template>
  <div class="grid">
    <slot />
    <Message v-if="status" :severity="status.severity">
      {{ status.message }}
    </Message>
    <Message v-else severity="secondary" icon="pi pi-clipboard" :closable="false">
      {{ info }}
    </Message>
  </div>
</template>

<style scoped>
.grid {
  min-width: 300px;
  min-height: 150px;
  display: grid;
  place-items: center;
  gap: 0.5rem;
}

:deep(.p-message) {
  font-size: smaller;
  margin: 0;
}
</style>
