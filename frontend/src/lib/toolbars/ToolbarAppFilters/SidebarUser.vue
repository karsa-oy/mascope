<script setup>
import { ref, watchEffect } from 'vue'

import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import ToggleSwitch from 'primevue/toggleswitch'

import { useApp } from '@/stores'

const app = useApp()

const drawer = ref()

watchEffect(() => {
  if (app.ui.darkmode.active) {
    document.documentElement.classList.add('darkmode')
    localStorage.setItem('mascope-darkmode', 'true')
  } else {
    document.documentElement.classList.remove('darkmode')
    localStorage.setItem('mascope-darkmode', 'false')
  }
})
</script>

<template>
  <Button
    v-tooltip.bottom="'Account'"
    icon="pi pi-user"
    severity="secondary"
    text
    @click="
      (event) => {
        drawer = true
      }
    "
  />
  <Drawer v-model:visible="drawer" header="Account" position="left" style="width: 350px">
    <section>
      <div class="row">
        <div>
          <h4>{{ app.auth.user.username }}</h4>
          <i>{{ app.auth.user.email }}</i>
        </div>
        <Button
          icon="pi pi-sign-out"
          label="Logout"
          @click="app.auth.logout"
          style="margin-top: 1rem"
        />
      </div>
    </section>
    <section>
      <h4>Theme</h4>
      <div class="row" style="width: fit-content">
        <span>Light</span>
        <span class="pi pi-sun" />
        <ToggleSwitch v-model="app.ui.darkmode.active" />
        <span class="pi pi-moon" />
        <span>Dark</span>
      </div>
    </section>
  </Drawer>
</template>

<style scoped>
.col {
  gap: 0rem;
}
</style>
