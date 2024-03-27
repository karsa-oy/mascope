<script setup>
import { computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { dialog } from '@/main'

import { useAppStore, useKeyStore } from '@/stores'

const appStore = useAppStore()
const keyStore = useKeyStore()

// load data

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

// return to home page at reload
const router = useRouter()
if (router.currentRoute !== '/') router.push('/')

watch(
  computed(() => appStore.pushNotification?.message),
  () => {
    dialog.alert(appStore.pushNotification?.message)
  }
)
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

<style>
.columns {
  margin: 0 auto;
  width: 100%;
  max-width: 1200px;
}
</style>
