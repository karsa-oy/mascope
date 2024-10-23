<script setup>
import { ref, watch} from 'vue'

import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'
import Panel from 'primevue/panel'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'

import { beautifySnakeCase } from '@/lib/utils'
import { BaseKarsaLogo } from '@/lib/base'
import { useApp } from '@/stores'
import { PaneLogin, PaneSignup } from '@/lib/panes'

const app = useApp()
const toast = useToast()

// toaster
app.ui.notification
  .on('*', ({ status, type, message }) => {
    if (status !== 'pending') {
      const severity =
        {
          warning: 'warn'
        }[status] ?? status

      const duration = status === 'error' ? 10000 : status === 'warning' ? 7000 : 3000

      toast.add({
        severity,
        summary: `${beautifySnakeCase(type)} ${status}`,
        detail: message,
        life: duration
      })
    }
  })
  .unmount()

  app.auth.identify()

  const tab = ref('login')

  const gotoLogin = () => {
    tab.value = "login"
  }
</script>

<template>
  <!-- App Routes -->
  <RouterView v-if="app.auth.user"/>
  <!-- Login / Signup Screen  -->
  <div v-else class="center" style="min-height: 80vh">
      <Panel style="width: 500px">
        <BaseKarsaLogo />
        <Tabs v-model:value="tab">
          <TabList>
            <Tab value="login">
              <a v-ripple @click="tab = 'login'" class="row">
                  <i class="pi pi-sign-in" />
                  <span>Login</span>
              </a>
            </Tab>
            <Tab value="signup">
              <a v-ripple @click="tab = 'signup'" class="row">
                  <i class="pi pi-signup" />
                  <span>Sign up</span>
              </a>
            </Tab>
          </TabList>
        </Tabs>
        <PaneLogin v-if="tab == 'login'"/>
        <PaneSignup v-if="tab == 'signup'" @signup="gotoLogin"/>
      </Panel>
  </div>
  <Toast position="bottom-right" v-if="!app.ui.notification.drawer" />
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
