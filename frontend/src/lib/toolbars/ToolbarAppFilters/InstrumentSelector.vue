<script setup>
import { ref, watch } from 'vue'

import Select from 'primevue/select'

import { useApp } from '@/stores'

const app = useApp()

/**
 * Watch for when instrument data is loaded, then focus on the saved instrument.
 * If the saved instrument is not available, fallback to the first instrument in the list.
 * The watcher only has an effect if no instrument is focused.
 */
watch(
  () => app.data.instrument.list.length,
  (count) => {
    if (count > 0 && !app.data.instrument.focused) {
      const saved = app.data.instrument.list.find(
        ({ instrument }) => instrument === localStorage.getItem('mascope-instrument')
      )
      if (saved) {
        app.data.instrument.focused = saved
      }
    }
  },
  { immediate: true }
)

/**
 * Sync focused instrument with the saved one in localStorage.
 */
watch(
  () => app.data.instrument.focused,
  (instrument) => {
    if (instrument) {
      localStorage.setItem('mascope-instrument', instrument.instrument)
    }
  }
)
</script>

<template>
  <label for="instrument-selector" class="hidden">Instrument selector</label>
  <Select
    inputId="instrument-selector"
    v-model="app.data.instrument.focused"
    :options="app.data.instrument.list"
    dataKey="instrument"
    optionLabel="instrument"
    appendTo="self"
  >
    <template #value="{ value }">
      <span v-if="value?.instrument">
        {{ value.instrument }}
      </span>
      <i v-else> None </i>
    </template>
    <template #dropdownicon>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="20"
        height="20"
        fill="currentColor"
        viewBox="0 0 256 256"
      >
        <path
          d="M224,208H203.94A88.05,88.05,0,0,0,144,64.37V32a16,16,0,0,0-16-16H80A16,16,0,0,0,64,32V136a16,16,0,0,0,16,16h48a16,16,0,0,0,16-16V80.46A72,72,0,0,1,181.25,208H32a8,8,0,0,0,0,16H224a8,8,0,0,0,0-16Zm-96-72H80V32h48V136ZM72,184a8,8,0,0,1,0-16h64a8,8,0,0,1,0,16Z"
        ></path>
      </svg>
    </template>
  </Select>
</template>
