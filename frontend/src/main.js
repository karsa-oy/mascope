import { createApp } from 'vue'
import { createPinia } from 'pinia'

import 'primevue/resources/themes/aura-dark-green/theme.css'
import Tooltip from 'primevue/tooltip'

import buefy from '@ntohq/buefy-next'
import '@mdi/font/css/materialdesignicons.min.css'

import { apiPlugin } from '@/api'

import App from './App.vue'
import router from './router'

const pinia = createPinia()
pinia.use(apiPlugin)

const app = createApp(App)

// boilerplate
app.use(pinia)
app.use(router)

// prime
app.directive('tooltip', Tooltip)

// buefy
app.use(buefy)

app.mount('#app')

import { DialogProgrammatic, ToastProgrammatic } from '@ntohq/buefy-next'

export const dialog = new DialogProgrammatic(app)
export const toast = new ToastProgrammatic(app)
