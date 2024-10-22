<script setup>
import Popover from 'primevue/popover'
import Button from 'primevue/button'

import { ref } from 'vue'

import { useApp } from '@/stores'

const app = useApp()

const popover = ref()
</script>

<template>
  <Button
    icon="pi pi-user"
    severity="secondary"
    text
    size="small"
    v-tooltip.bottom="'User'"
    @click="
      (event) => {
        popover.toggle(event)
      }
    "
  />
  <Popover ref="popover">
    <menu>
      <h4>{{app.auth.user.username}}</h4>
      <i>{{app.auth.user.email }}</i>
      <Button label="Logout" @click="app.auth.logout"/>
    </menu>
  </Popover>
</template>

<style scoped>
  menu {
    display: flex;
    flex-flow: column;
    justify-content: flex-end;
    text-align: right;
    gap: 1rem;
    padding: 0.5rem;
  }
  menu > :deep(*) {
    margin: 0;
  }
</style>
