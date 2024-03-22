import { createApp } from 'vue'
import { createPinia } from 'pinia'

import buefy from '@ntohq/buefy-next'
import '@mdi/font/css/materialdesignicons.min.css'

import App from './App.vue'
import router from './router'

import { apiPlugin } from '@/stores/plugins/api.js'

const pinia = createPinia()
pinia.use(apiPlugin)

const app = createApp(App)
app.use(pinia)
app.use(router)
app.use(buefy)

app.mount('#app')
