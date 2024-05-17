import { createApp } from 'vue'
import { createPinia } from 'pinia'

import PrimeVue from 'primevue/config'

import Tooltip from 'primevue/tooltip'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import Ripple from 'primevue/ripple'

import 'primeicons/primeicons.css'

import { apiPlugin } from '@/api'

import App from './App.vue'
import router from './routes'
import Karsa from './theme.js'

const pinia = createPinia()
pinia.use(apiPlugin)

const app = createApp(App)

// boilerplate
app.use(pinia)
app.use(router)

// theme

// prime
app.use(PrimeVue, {
  // Default theme configuration
  theme: {
    preset: Karsa,
    options: {
      prefix: 'p',
      darkModeSelector: '.darkmode',
      cssLayer: true
    }
  },
  ripple: true
})

app.use(ConfirmationService)
app.use(ToastService)
app.directive('tooltip', Tooltip)
app.directive('ripple', Ripple)

app.mount('#app')
