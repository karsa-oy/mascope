<script setup>
import { ref, reactive, computed, watchEffect, watch } from 'vue'

import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Button from 'primevue/button'

import { api } from '@/api'
import { useApp } from '@/stores'
import { BaseCopyableField, BaseEditableField } from '@/lib/base'
import { DialogUserManagement, DialogPasswordChange } from '@/lib/dialogs'
import { prettyRoleName, ROLES } from '@/lib/roles'

import { useSidebarMenu } from './state.js'

const app = useApp()
const sidebarMenu = useSidebarMenu()

const open = computed(() => sidebarMenu.open && sidebarMenu.tab === 'settings')

const dialog = reactive({
  users: false,
  password: false
})

// TODO_config API Token Management
const SERVICE_CONFIGS = [
  {
    id: 'mascope_sdk', // used for both internal reference in selectedTokenType and API requests for packages
    label: 'Jupyter Notebooks',
    minRole: 100 // guest role_id
  },
  {
    id: 'tof-agent', // Different delimiter styles (_ vs -) are used in id (packages/libraries use _, services/agents use -).
    label: 'TOF Agent',
    minRole: 200 // editor role_id
  },
  {
    id: 'file-agent',
    label: 'File Agent',
    minRole: 200 // editor role_id
  },
  {
    id: 'export-agent',
    label: 'CSV Export Agent',
    minRole: 200 // editor role_id
  }
]

const token = ref(null)
const selectedTokenType = ref('mascope_sdk')

const currentServiceConfig = computed(() =>
  SERVICE_CONFIGS.find((c) => c.id === selectedTokenType.value)
)

// Available token types based on user role
const availableTokenTypes = computed(() =>
  SERVICE_CONFIGS.filter((config) => app.auth.user.role_id >= config.minRole)
)

const tokenItems = computed(() =>
  availableTokenTypes.value.map((config) => ({
    value: config.id,
    label: config.label
  }))
)

const regenerateToken = async () => {
  const config = currentServiceConfig.value
  if (!config) return
  try {
    token.value = (
      await api.http.post(`/auth/access_token/regenerate`, {
        service_name: config.id
      })
    )?.data?.access_token
  } catch (e) {
    app.ui.notification.push({
      type: `${config.id}_token_refresh`,
      status: 'error',
      message: `${e?.response?.data?.error || e?.message}`
    })
  }
}

// Clear state when closing drawer
const clear = () => {
  token.value = null
  selectedTokenType.value = 'mascope_sdk'
}

// Watch drawer visibility to clear state
watch(open, (visible) => {
  if (!visible) clear()
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

const layer = 'sidebar_settings_tab'
watchEffect(() => {
  if (open.value) {
    app.ui.help.set(layer)
  }
})

const vHelpLayer = app.ui.help.directive(layer)
</script>

<template>
  <h2>Settings</h2>
  <section
    v-help-layer.right="
      `
    <b>Account Settings</b>
    <p>View your sign-in details, user role, and change your password.</p>
  `
    "
  >
    <h3>Account</h3>
    <BaseEditableField
      :field="app.auth.user.username"
      :save="(username) => app.data.user.update({ username })"
    />
    <ul>
      <li>📧 {{ app.auth.user.email }}</li>
      <li>{{ prettyRoleName(app.auth.user) }}</li>
    </ul>
    <Button
      label="Change password"
      @click="() => (dialog.password = true)"
      severity="secondary"
      text
      icon="pi ph ph-lock-key"
    />
  </section>
  <section
    v-help-layer.right="
      `
    <b>Theme</b>
    <p>Select between light and dark mode for the Mascope interface.</p>
  `
    "
  >
    <h3>Theme</h3>
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
      `
      <b>API Access Tokens</b>
      <p>
        API tokens are used for authentication when accessing Mascope programmatically,
        e.g., from Jupyter Notebooks or other external tools. Here you can generate tokens
        for specific services.
      </p>
    `
    "
  >
    <h3>API Access Tokens</h3>
    <div id="token-container">
      <div id="token-controls">
        <Select
          v-model="selectedTokenType"
          :options="tokenItems"
          optionLabel="label"
          optionValue="value"
          id="token-service-select"
          @change="token = null"
        />
        <Button
          icon="pi pi-refresh"
          label="Regenerate"
          @click="regenerateToken"
          id="token-button"
        />
      </div>
      <div v-if="token" id="token-info">
        <div id="token-display">
          <span class="pi pi-lock" style="opacity: 0.3" />
          <BaseCopyableField :field="token" />
        </div>
        <Message icon="pi pi-info-circle" severity="info" closable>
          <p>Token is shown only once for security reasons; if you lose it, regenerate a new one</p>
        </Message>
      </div>
    </div>
  </section>
  <section
    v-if="app.auth.user.role_id >= ROLES.admin"
    v-help-layer.right="
      `
  <b>Admin Settings</b>
  <p>Add, remove and modify users</p>
  `
    "
  >
    <h3>Admin</h3>
    <Button icon="pi pi-users" @click="() => (dialog.users = true)" label="Manage users" />
  </section>
  <DialogUserManagement v-model:visible="dialog.users" />
  <DialogPasswordChange v-model:visible="dialog.password" />
</template>

<style scoped>
.col {
  gap: 0rem;
}

#token-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 3rem;

  #token-controls {
    display: flex;
    align-items: flex-start;
    gap: 1.5rem;
    width: 100%;

    #token-button {
      flex-shrink: 0;
    }

    #token-service-select {
      width: 100%;
    }
  }

  #token-info {
    display: flex;
    flex-direction: column;
    gap: 1rem;

    #token-display {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      border: 1px solid var(--p-drawer-border-color);
      padding: 0.75rem;
      border-radius: 1rem;
      font-size: smaller;
      width: 100%;
      word-break: break-all;
    }
  }
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
