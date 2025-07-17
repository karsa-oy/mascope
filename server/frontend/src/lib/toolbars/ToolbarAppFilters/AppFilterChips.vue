<script setup>
import { ref, watchEffect, provide } from 'vue'

import { useMagicKeys } from '@vueuse/core'

import FilterSample from './FilterSample.vue'

const { alt, c } = useMagicKeys()

// provide a registration API
const filters = ref([])
provide('register-filter', (filter) => {
  filters.value.push(filter)
})

// clear all filters when alt+c is pressed
watchEffect(() => {
  if (alt.value && c.value) {
    filters.value.forEach(({ clear }) => clear())
  }
})

const filtering = defineModel('filtering')
watchEffect(() => {
  filtering.value = filters.value.some(({ active }) => active)
})
</script>

<template>
  <menu>
    <span v-if="filtering" class="pi pi-filter" style="opacity: 0.5" />
    <FilterSample />
  </menu>
</template>

<style scoped>
menu {
  display: flex;
  flex-flow: row;
  align-items: center;
  gap: 0.5rem;
  padding: 0;
}
</style>
