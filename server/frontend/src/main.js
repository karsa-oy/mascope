import { createApp } from 'vue'
import { createPinia } from 'pinia'

import PrimeVue from 'primevue/config'

import Tooltip from 'primevue/tooltip'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import Ripple from 'primevue/ripple'

import 'primeicons/primeicons.css'
import '@phosphor-icons/web/regular'
// Self-hosted Inter (weight 400, matching the former Google Fonts stylesheet);
// fonts must not be fetched from third-party CDNs (GDPR: IP disclosure to Google)
import '@fontsource/inter'

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

/** 
  Patch addEventListener to add passive flag for scroll-blocking events
  This is to get rid of "[Violation] Added non-passive event listener to a
  scroll-blocking event" warnings in the console
*/
const originalAddEventListener = EventTarget.prototype.addEventListener
EventTarget.prototype.addEventListener = function (type, listener, options) {
  const scrollBlockingEvents = ['touchstart', 'touchmove', 'wheel']
  if (scrollBlockingEvents.includes(type) && options !== true && typeof options !== 'object') {
    options = { passive: true }
  } else if (
    scrollBlockingEvents.includes(type) &&
    typeof options === 'object' &&
    options.passive !== false
  ) {
    options = { ...options, passive: true }
  }
  return originalAddEventListener.call(this, type, listener, options)
}
