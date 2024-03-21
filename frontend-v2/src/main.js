import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import buefy from '@ntohq/buefy-next'
import '@mdi/font/css/materialdesignicons.min.css'

const app = createApp(App)
const store = createPinia()

app.use(store)
app.use(router)
app.use(buefy)

app.mount('#app')
