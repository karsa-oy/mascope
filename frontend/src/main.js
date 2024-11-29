import { createApp } from 'vue'
import { createPinia } from 'pinia'

import PrimeVue from 'primevue/config'

import Tooltip from 'primevue/tooltip'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import Ripple from 'primevue/ripple'

import 'primeicons/primeicons.css'

import App from './App.vue'
import router from './routes'
import Karsa from './theme.js'

import { useHelp } from './stores/ui/help'

const app = createApp(App)

// routing
app.use(router)

// prime
app.use(PrimeVue, {
  // theme
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

// store
const pinia = createPinia()
app.use(pinia)

// help
const help = useHelp()
app.directive('help', help.directive())

// init
app.mount('#app')
