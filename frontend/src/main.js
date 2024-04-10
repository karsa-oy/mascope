import { createApp } from 'vue'
import { createPinia } from 'pinia'

import buefy from '@ntohq/buefy-next'
import '@mdi/font/css/materialdesignicons.min.css'

import { apiPlugin } from '@/api'

import App from './App.vue'
import router from './router'

const pinia = createPinia()
pinia.use(apiPlugin)

const app = createApp(App)
app.use(pinia)
app.use(router)
app.use(buefy)

app.mount('#app')

import { DialogProgrammatic, ToastProgrammatic } from '@ntohq/buefy-next'

export const dialog = new DialogProgrammatic(app)
export const toast = new ToastProgrammatic(app)
