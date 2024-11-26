<script setup>
import { ref, watchEffect } from 'vue'

import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'

import { api } from '@/api'
import { useApp } from '@/stores'
import { BaseCopyableField } from '@/lib/base'

const app = useApp()

const drawer = ref()

const token = ref()

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
    <section>
      <h4>
        API Token
        <span
          class="pi pi-question-circle"
          v-tooltip="
            'API tokens are used for Jupyter notebooks and other development tools. Tokens can only be viewed once for security reasons.'
          "
        />
      </h4>
      <div class="row">
        <Button
          icon="pi pi-id-card"
          label="Regenerate"
          @click="
            async () => {
              try {
                await api.http.post(`/auth/access_token/remove`)
                token = (await api.http.post(`/auth/access_token/generate`))?.data?.access_token
              } catch (e) {
                console.error(e)
                app.ui.notification.push({
                  type: 'regenerate_api_token',
                  status: 'error',
                  message: 'regeneration failed'
                })
              }
            }
          "
        />
        <div class="token row" v-if="token">
          <span class="pi pi-lock" style="opacity: 0.3" />
          <BaseCopyableField :field="token" />
        </div>
      </div>
      <div v-if="token">
        <Message icon="pi pi-info-circle" severity="info" closable>
          <p>
            This token is only shown once for security reasons; if you lose it, regenerate a new one
            here.
          </p>
        </Message>
      </div>
    </section>
  </Drawer>
</template>

<style scoped>
.col {
  gap: 0rem;
}

.token {
  margin: 1rem;
  border: 1px solid var(--p-drawer-border-color);
  max-width: 180px;
  word-break: break-all;
  padding: 0.5rem;
  border-radius: 1rem;
  font-size: smaller;
}

section:not(:first-child) {
  margin-top: 2rem;
  border-top: 1px solid var(--p-drawer-border-color);
}
</style>
