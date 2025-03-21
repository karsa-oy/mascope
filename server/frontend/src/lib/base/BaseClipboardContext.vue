<script setup>
import { ref } from 'vue'

import Message from 'primevue/message'

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
  },
  hideInitMessage: {
    type: Boolean,
    required: false,
    default: false
  },
  persistMessage: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['validated', 'invalidated'])

const show = (severity, message) => {
  status.value = { severity, message }
  setTimeout(() => {
    status.value = null
  }, 3500)
}

async function process() {
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

let alive = ref(!props.hideInitMessage)
setTimeout(
  () => {
    alive.value = false
  },
  status.value ? 3000 : 2000
)
</script>

<template>
  <div class="grid" @paste="process">
    <slot />
    <template v-if="alive || persistMessage">
      <Message v-if="status" :severity="status.severity">
        {{ status.message }}
      </Message>
      <slot name="info">
        <Message severity="secondary" icon="pi pi-clipboard">
          {{ info }}
        </Message>
      </slot>
    </template>
  </div>
</template>

<style scoped>
.grid {
  position: relative;
  min-width: 300px;
  min-height: 200px;
  height: 100%;
  display: grid;
  place-items: center;
  gap: 0.5rem;
}

:deep(.p-message) {
  position: absolute;
  font-size: smaller;
  margin: auto;
  opacity: 0.8;
  width: 300px;
}
</style>
