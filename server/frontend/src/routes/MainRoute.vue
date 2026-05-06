<script setup>
import { computed } from 'vue'

import { BaseKarsaLogo } from '@/lib/base'

import Dashboard from './Dashboard.vue'
import ProgressSpinner from 'primevue/progressspinner'

import { useApp } from '@/stores'

const app = useApp()
const ready = computed(() => app.data.workspace.list.length > 0)
</script>

<template>
  <!-- App Dashboard  -->
  <div id="app" v-if="ready">
    <Dashboard />
  </div>
  <!-- Loading Spinner  -->
  <div id="loading" v-else>
    <div class="col">
      <BaseKarsaLogo />
      <ProgressSpinner />
      <strong>Loading...</strong>
    </div>
  </div>
</template>
