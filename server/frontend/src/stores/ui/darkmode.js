import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useDarkmode = defineStore('app.ui.darkmode', () => {
  // state
  const active = ref(true)

  // init darkmode
  const systemPreference = window.matchMedia('(prefers-color-scheme:dark)').matches
  const savedPreference =
    localStorage.getItem('mascope-darkmode') == 'true'
      ? true
      : localStorage.getItem('mascope-darkmode') == 'false'
        ? false
        : null
  active.value = savedPreference ?? systemPreference ?? true
  if (active.value) {
    document.documentElement.classList.add('darkmode')
  }

  return {
    active
  }
})
