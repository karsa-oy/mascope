<script setup>
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'

import { DialogProgrammatic as dialog } from '@ntohq/buefy-next'

import { useAppStore, useKeyStore, useNotificationStore } from '@/stores'

const appStore = useAppStore()
const keyStore = useKeyStore()
const notificationStore = useNotificationStore()

// load data

appStore.load()

const isDevelopmentMode = computed(() => appStore.mode === 'development')

// add event listeners
window.addEventListener('keydown', (event) => {
  keyStore.down(event)
})
window.addEventListener('keyup', (event) => {
  keyStore.up(event)
})

// return to home page at reload
const router = useRouter()
if (router.currentRoute !== '/') router.push('/')

// warn if in dev mode
if (isDevelopmentMode.value) {
  notificationStore.showWarningNotification({
    notification: 'inDevelopment'
  })
}

watch(appStore.pushNotification?.message, () => {
  console.log(appStore)
  dialog.alert(appStore.pushNotification?.message)
})
</script>

<template>
  <div id="app">
    <div v-if="appStore.ready">
      <router-view></router-view>
    </div>
    <b-loading :active="!appStore.ready" :is-full-page="true"> </b-loading>
  </div>
</template>

<style lang="scss">
@import './assets/style.scss';
</style>
