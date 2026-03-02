import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useIonTableCustomizer = defineStore('browser.match.ion.customizer', () => {
  const popover = ref()
  const config = ref({})

  function show(event) {
    popover.value?.show(event)
  }

  function hide() {
    popover.value?.hide()
  }

  return {
    show,
    hide,
    popover,
    config
  }
})
