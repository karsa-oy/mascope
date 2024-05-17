<script setup>
import { onMounted } from 'vue'

import ProgressSpinner from 'primevue/progressspinner'
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import { beautifySnakeCase } from '@/lib/utils'
import { BaseKarsaLogo } from '@/lib/base'
import { useAppStore, useNotification, useKeyStore } from '@/stores'

const toast = useToast()

const appStore = useAppStore()
const keyStore = useKeyStore()

const notification = useNotification()

// init

appStore.load()

onMounted(() => {
  // add event listeners
  window.addEventListener('keydown', (event) => {
    keyStore.down(event)
  })
  window.addEventListener('keyup', (event) => {
    keyStore.up(event)
  })
})

// toaster

const cleanup = notification.on('*', ({ status, type, message }) => {
  if (status !== 'pending') {
    const severity =
      {
        warning: 'warn'
      }[status] ?? status
    toast.add({
      severity,
      summary: `${beautifySnakeCase(type)} ${status}`,
      detail: message,
      life: status === 'error' ? 10000 : 3000
    })
  }
})
cleanup()
</script>

<template>
  <div id="app" v-if="appStore.ready">
    <RouterView />
  </div>
  <div id="loading" v-else>
    <div class="col">
      <BaseKarsaLogo />
      <ProgressSpinner />
      <strong>Loading...</strong>
    </div>
  </div>
  <Toast position="bottom-right" />
  <ConfirmDialog />
</template>

<style>
@import './style.css';

#loading {
  width: 100vw;
  height: 100vh;
  display: grid;
  place-items: center;
}
.col {
  gap: 5rem;
}
strong {
  opacity: 0.5;
}
</style>
