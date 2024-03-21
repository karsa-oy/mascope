import { createApp } from 'vue'
import store from './store'
import buefy from '@ntohq/buefy-next'
import '@mdi/font/css/materialdesignicons.min.css'

import App from './App.vue'
import routes from './router.js'

createApp(App).use(store).use(routes).use(buefy).mount('#app')
