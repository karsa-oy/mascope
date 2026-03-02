<script setup>
import { ref, computed, watch, onMounted } from 'vue'

import Button from 'primevue/button'
import Popover from 'primevue/popover'
import Listbox from 'primevue/listbox'

import { useIonTableCustomizer } from './stores'

const customizer = useIonTableCustomizer()

const popoverRef = ref()
onMounted(() => {
  customizer.popover = popoverRef.value
  readConfig()
})

// Fixed column definitions for the ion table
const availableColumns = [
  { field: 'target_ion_formula', label: 'Ion' },
  { field: 'target_compound_name', label: 'Name' },
  { field: 'target_compound_formula', label: 'Compound' },
  { field: 'ionization_mechanism', label: 'Mechanism' }
]

const defaultConfig = {
  columns: [...availableColumns]
}

const isDefault = computed(
  () => JSON.stringify(customizer.config) === JSON.stringify(defaultConfig)
)
const isInitialized = computed(() => JSON.stringify(customizer.config) !== '{}')

// Global localStorage key
const STORAGE_KEY = 'match-browser-ion-table'

// Write to local storage
function writeConfig() {
  if (!isInitialized.value) return
  if (isDefault.value) {
    localStorage.removeItem(STORAGE_KEY)
  } else {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(customizer.config))
  }
}

// Read from local storage, falling back on default
function readConfig() {
  const storedState = localStorage.getItem(STORAGE_KEY)
  customizer.config = storedState
    ? JSON.parse(storedState)
    : { ...defaultConfig, columns: [...defaultConfig.columns] }
}

// Reset to default config and clear local storage
function resetConfig() {
  customizer.config = { ...defaultConfig, columns: [...defaultConfig.columns] }
  localStorage.removeItem(STORAGE_KEY)
}

// Write to local storage when any options update
watch(() => customizer.config, writeConfig, { deep: true })
</script>

<template>
  <Button
    v-tooltip.top="'Configure column visibility'"
    icon="pi pi-cog"
    severity="secondary"
    text
    size="small"
    @click="
      (event) => {
        event.stopPropagation()
        customizer.show(event)
      }
    "
  />
  <Popover ref="popoverRef" contentStyle="height: fit-content;">
    <div class="row" style="margin-bottom: 0.5rem">
      <Button
        label="Reset"
        icon="pi pi-replay"
        severity="secondary"
        iconPos="right"
        text
        @click="resetConfig"
        v-tooltip.right="'Reset table configuration'"
      />
    </div>
    <Listbox
      v-model="customizer.config.columns"
      :options="availableColumns"
      multiple
      optionLabel="label"
      dataKey="field"
    />
  </Popover>
</template>
