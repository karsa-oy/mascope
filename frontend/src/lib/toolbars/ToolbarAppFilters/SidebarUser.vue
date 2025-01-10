<script setup>
import { ref, reactive, watchEffect } from 'vue'

import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'
import InputText from 'primevue/inputtext'

import { api } from '@/api'
import { useApp } from '@/stores'
import { BaseCopyableField, BaseEditableField } from '@/lib/base'
import { beautifySnakeCase } from '@/lib/utils'
import { DialogUserManagement, DialogPasswordChange } from '@/lib/dialogs'
import { prettyRoleName } from '@/lib/roles'

const app = useApp()

const drawer = ref()

const token = ref()

const dialog = reactive({
  users: false,
  password: false
})

watchEffect(() => {
  if (app.ui.darkmode.active) {
    document.documentElement.classList.add('darkmode')
    localStorage.setItem('mascope-darkmode', 'true')
  } else {
    document.documentElement.classList.remove('darkmode')
    localStorage.setItem('mascope-darkmode', 'false')
  }
})

const layer = 'user_sidebar'
watchEffect(() => {
  app.ui.help.set(drawer.value ? layer : null)
})

const vHelpLayer = app.ui.help.directive(layer)
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
    :pt="
      app.ui.help.bottom_start(`
          <h1>User Sidebar</h1>

          <p>Manage your account, pick between light/dark theme
          and generate API tokens.</p>

          <p>Admin users can access admin features here.</p>
    `)
    "
  />
  <Drawer v-model:visible="drawer" header="Account" position="left" style="width: 350px">
    <section v-help-layer.right="'Manage your sign-in details and session'">
      <div class="row">
        <div>
          <h4>
            <BaseEditableField
              :field="app.auth.user.username"
              :save="(username) => app.data.user.update({ username })"
            />
          </h4>
          <ul>
            <li>📧 {{ app.auth.user.email }}</li>
            <li>{{ prettyRoleName(app.auth.user) }}</li>
          </ul>
        </div>
        <div class="col" style="gap: 2rem; align-items: flex-end">
          <Button
            icon="pi pi-sign-out"
            label="Logout"
            @click="app.auth.logout"
            style="margin-top: 1rem"
          />
          <Button
            label="Change password"
            @click="() => (dialog.password = true)"
            severity="secondary"
            text
          />
        </div>
      </div>
    </section>
    <section v-help-layer.right="'Pick the theme for Mascope'">
      <h4>Theme</h4>
      <div class="row" style="width: fit-content">
        <span>Light</span>
        <span class="pi pi-sun" />
        <ToggleSwitch v-model="app.ui.darkmode.active" />
        <span class="pi pi-moon" />
        <span>Dark</span>
      </div>
    </section>
    <section
      v-help-layer.right="
        'API tokens are used for Jupyter notebooks and other development tools. Tokens can only be viewed once for security reasons.'
      "
    >
      <h4>API Token</h4>
      <div class="row">
        <Button
          icon="pi pi-id-card"
          label="Regenerate"
          @click="
            async () => {
              try {
                await api.http.post(`/auth/access_token/remove`, {
                  service_name: `mascope_api`
                })
                token = (
                  await api.http.post(`/auth/access_token/generate`, {
                    service_name: `mascope_api`
                  })
                )?.data?.access_token
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
    <section
      v-if="app.auth.user.role_id >= 300"
      v-help-layer.right="'Add, remove and modify users'"
    >
      <h4>Admin</h4>
      <Button icon="pi pi-users" @click="() => (dialog.users = true)" label="Manage users" />
    </section>
  </Drawer>
  <DialogUserManagement v-model:visible="dialog.users" />
  <DialogPasswordChange v-model:visible="dialog.password" />
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

ul {
  list-style: none;
  padding-left: 0.5em;

  li {
    margin: 0.7rem 0;

    i {
      margin-right: 0.2rem;
    }
  }
}
</style>
